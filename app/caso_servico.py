"""Carga, exportação e duplicação de casos (JSON <-> banco)."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from .config import BASE_DIR
from .models_caso import (Caso, Contrato, Evento, FichaTecnica, Funcionario, Inconsistencia, Item, Parametro,
                          Socio)

CASO_BASE = BASE_DIR / "dados" / "caso_base" / "eh0012_2026_2.json"


# ------------------------------------------------------------------ números
def num(v) -> float | None:
    """Converte '1.234,56', 'R$ 9,0867', '3,5%' ou 1234.56 em float. Texto não numérico -> None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace("%", "").replace(" ", "")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):  # 385.000 -> milhar no padrão brasileiro
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def fmt_unit(v) -> str:
    """Valor unitário: no mínimo 4 casas e até 8 (custos do caso-base com a precisão do exercício)."""
    if v is None or v == "" or isinstance(v, str):
        return fmt(v)
    return fmt(v, next((c for c in (4, 5, 6, 7, 8) if abs(round(v, c) - v) < 1e-9), 8))


def fmt(v, casas: int | None = None) -> str:
    """Formata número no padrão brasileiro; mantém texto como está."""
    if v is None or v == "":
        return ""
    if isinstance(v, str):
        return v
    if casas is None:
        if float(v).is_integer():
            casas = 0 if abs(v) < 1000 or isinstance(v, int) else 2
        else:
            casas = next((c for c in (2, 4, 5, 6, 7, 8) if abs(round(v, c) - v) < 1e-9), 4)
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _data(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


# ------------------------------------------------------------------ carga
def _add_params(caso: Caso, escopo: str, ref: str, lista: list[dict], ordem0: int = 0) -> None:
    for i, p in enumerate(lista or []):
        base = p.get("base")
        caso.parametros.append(Parametro(
            escopo=escopo, ref=ref or "", nome=p["nome"], unidade=p.get("unidade"),
            base=(fmt(base) if not isinstance(base, str) else base),
            minimo=num(p.get("min")), maximo=num(p.get("max")), passo=num(p.get("passo")),
            regra=p.get("regra"), varia=p.get("varia", "min" in p), ordem=ordem0 + i,
        ))


def carregar(db: Session, dados: dict, nome: str, docente_id: int | None = None, origem_id: int | None = None) -> Caso:
    emp = dict(dados.get("empresa", {}))
    params_emp = []
    for chave in ("capital_social",):
        if isinstance(emp.get(chave), dict):
            params_emp.append(emp.pop(chave))
    dest = emp.pop("destinacao_resultado", {}) or {}
    for k, v in list(dest.items()):
        if isinstance(v, dict) and "nome" in v:
            params_emp.append(v)
        elif isinstance(v, dict):
            emp[f"destinacao - {k.replace('_', ' ')}"] = f"{fmt(v.get('base'))} ({v.get('regra', '')})".strip()
        else:
            emp[f"destinacao - {k.replace('_', ' ')}"] = v
    markup = dict(dados.get("markup", {}))
    param_markup = markup.pop("parametro", None)

    caso = Caso(nome=nome, descricao=dados.get("caso"), docente_id=docente_id, origem_id=origem_id, dados={
        "empresa": {k: (", ".join(v) if isinstance(v, list) else v) for k, v in emp.items()},
        "saldos_iniciais": dados.get("saldos_iniciais", {}),
        "imobilizado": dados.get("imobilizado", []),
        "vida_util": dados.get("vida_util", []),
        "rateio_areas": dados.get("rateio_areas", []),
        "folha_regras": {k: ("; ".join(f"{a}: {b}" for a, b in v.items()) if isinstance(v, dict) else v)
                         for k, v in (dados.get("folha_regras") or {}).items()},
        "plano_producao": dados.get("plano_producao", {}),
        "markup": markup,
    })
    db.add(caso)
    _add_params(caso, "empresa", "", params_emp)
    _add_params(caso, "socios", "", dados.get("parametros_socios"))
    _add_params(caso, "folha", "", dados.get("parametros_folha"))
    _add_params(caso, "producao", "", dados.get("parametros_producao"))
    if param_markup:
        _add_params(caso, "markup", "", [param_markup])
    for s in dados.get("socios", []):
        caso.socios.append(Socio(
            nome=s["nome"], funcao=s.get("funcao"), cotas=s.get("cotas"), a_integralizar=num(s.get("a_integralizar")),
            evento_integralizacao=s.get("integralizacao_evento") or s.get("evento_integralizacao"),
            pro_labore_jan=num(s.get("pro_labore_jan")), pro_labore_fev=num(s.get("pro_labore_fev")),
            dependentes=s.get("dependentes")))
    for c in dados.get("contratos", []):
        caso.contratos.append(Contrato(
            codigo=c["id"], tipo=c["tipo"], parte=c.get("parte"), inicio=_data(c.get("inicio")),
            descricao=c.get("descricao"), eventos=", ".join(c.get("eventos", [])) if isinstance(c.get("eventos"), list) else c.get("eventos")))
        _add_params(caso, "contrato", c["id"], c.get("parametros"))
    for i, f in enumerate(dados.get("funcionarios", [])):
        caso.funcionarios.append(Funcionario(ordem=i, **{k: f.get(k) for k in (
            "setor", "nome", "admissao", "salario_jan", "he_jan", "comissao_jan", "dependentes_jan",
            "salario_fev", "he_fev", "comissao_fev", "dependentes_fev")}))
    for i, it in enumerate(dados.get("itens", [])):
        caso.itens.append(Item(ordem=i, codigo=it["codigo"], descricao=it["descricao"], tipo=it["tipo"], ncm=it.get("ncm"),
                               custo_base=it.get("custo_base"), custo_min=it.get("custo_min"), custo_max=it.get("custo_max")))
    for prod, comp in (dados.get("ficha_tecnica") or {}).items():
        for insumo, q in comp.items():
            caso.ficha.append(FichaTecnica(produto=prod, insumo=insumo, quantidade=float(q)))
    for e in dados.get("eventos", []):
        caso.eventos.append(Evento(codigo=e["id"], data=_data(e["data"]), grupo=e.get("grupo"), descricao=e["descricao"],
                                   natureza=e.get("natureza", "V"), contrato=e.get("contrato"), obs=e.get("obs")))
        _add_params(caso, "evento", e["id"], e.get("parametros"))
    for x in dados.get("inconsistencias", []):
        caso.inconsistencias.append(Inconsistencia(onde=x["onde"], descricao=x["descricao"], decisao=x.get("decisao"),
                                                   status=x.get("status", "PENDENTE")))
    db.flush()
    return caso


def carregar_caso_base(db: Session, nome: str = "EH0012 · Caso-base 2026.2", docente_id: int | None = None) -> Caso:
    dados = json.loads(Path(CASO_BASE).read_text(encoding="utf-8"))
    return carregar(db, dados, nome, docente_id)


# ------------------------------------------------------------------ exportação
def _p(p: Parametro) -> dict:
    d = {"nome": p.nome, "base": p.base, "unidade": p.unidade, "varia": p.varia}
    if p.minimo is not None or p.maximo is not None:
        d.update({"min": p.minimo, "max": p.maximo, "passo": p.passo})
    if p.regra:
        d["regra"] = p.regra
    return d


def exportar(caso: Caso) -> dict:
    d = caso.dados or {}
    empresa = dict(d.get("empresa", {}))
    return {
        "caso": caso.descricao or caso.nome, "nome": caso.nome, "formato": "labcont-caso/1",
        "empresa": empresa,
        "parametros_empresa": [_p(p) for p in caso.params("empresa")],
        "socios": [{"nome": s.nome, "funcao": s.funcao, "cotas": s.cotas, "a_integralizar": s.a_integralizar,
                    "evento_integralizacao": s.evento_integralizacao, "pro_labore_jan": s.pro_labore_jan,
                    "pro_labore_fev": s.pro_labore_fev, "dependentes": s.dependentes} for s in caso.socios],
        "parametros_socios": [_p(p) for p in caso.params("socios")],
        "saldos_iniciais": d.get("saldos_iniciais", {}), "imobilizado": d.get("imobilizado", []),
        "vida_util": d.get("vida_util", []), "rateio_areas": d.get("rateio_areas", []),
        "contratos": [{"id": c.codigo, "tipo": c.tipo, "parte": c.parte, "inicio": c.inicio.isoformat() if c.inicio else None,
                       "descricao": c.descricao, "eventos": [e.strip() for e in (c.eventos or "").split(",") if e.strip()],
                       "parametros": [_p(p) for p in caso.params("contrato", c.codigo)]} for c in caso.contratos],
        "folha_regras": d.get("folha_regras", {}),
        "parametros_folha": [_p(p) for p in caso.params("folha")],
        "funcionarios": [{k: getattr(f, k) for k in ("setor", "nome", "admissao", "salario_jan", "he_jan", "comissao_jan",
                                                     "dependentes_jan", "salario_fev", "he_fev", "comissao_fev",
                                                     "dependentes_fev")} for f in caso.funcionarios],
        "itens": [{"codigo": i.codigo, "descricao": i.descricao, "tipo": i.tipo, "ncm": i.ncm, "custo_base": i.custo_base,
                   "custo_min": i.custo_min, "custo_max": i.custo_max} for i in caso.itens],
        "ficha_tecnica": _ficha_dict(caso),
        "plano_producao": d.get("plano_producao", {}),
        "parametros_producao": [_p(p) for p in caso.params("producao")],
        "markup": {**d.get("markup", {}), **({"parametro": _p(caso.params("markup")[0])} if caso.params("markup") else {})},
        "eventos": [{"id": e.codigo, "data": e.data.isoformat() if e.data else None, "grupo": e.grupo, "descricao": e.descricao,
                     "natureza": e.natureza, "contrato": e.contrato, "obs": e.obs,
                     "parametros": [_p(p) for p in caso.params("evento", e.codigo)]} for e in caso.eventos],
        "inconsistencias": [{"onde": x.onde, "descricao": x.descricao, "decisao": x.decisao, "status": x.status}
                            for x in caso.inconsistencias],
    }


def _ficha_dict(caso: Caso) -> dict:
    out: dict = {}
    for f in caso.ficha:
        out.setdefault(f.produto, {})[f.insumo] = f.quantidade
    return out


def importar(db: Session, dados: dict, nome: str | None = None, docente_id: int | None = None,
             origem_id: int | None = None) -> Caso:
    """Aceita tanto o formato do caso-base quanto o formato exportado."""
    dados = dict(dados)
    if "parametros_empresa" in dados:  # formato exportado
        emp = dict(dados.get("empresa", {}))
        params = dados.pop("parametros_empresa")
        if params:
            emp["capital_social"] = params[0]
            emp["destinacao_resultado"] = {f"p{i}": p for i, p in enumerate(params[1:])}
        dados["empresa"] = emp
    return carregar(db, dados, nome or dados.get("nome") or dados.get("caso") or "Caso importado", docente_id, origem_id)


def duplicar(db: Session, caso: Caso, nome: str, docente_id: int | None) -> Caso:
    return importar(db, exportar(caso), nome, docente_id, origem_id=caso.id)
