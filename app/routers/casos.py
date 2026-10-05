"""Telas do caso da empresa: empresa e sócios, contratos, folha, produção, eventos e inconsistências.

Todos os valores e faixas são editáveis. Cada professor pode duplicar o caso-base e ajustá-lo.
"""
from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..caso_servico import carregar_caso_base, duplicar, exportar, fmt, importar, num
from ..db import get_db
from ..main import render, voltar
from ..models import Docente
from ..models_caso import (ESCOPOS, Caso, Contrato, Evento, FichaTecnica, Funcionario, Inconsistencia, Item,
                           Parametro, Socio)

router = APIRouter()

ABAS = [("empresa", "Empresa e sócios"), ("contratos", "Contratos"), ("folha", "Folha"),
        ("producao", "Produção"), ("eventos", "Eventos"), ("inconsistencias", "Inconsistências"),
        ("gabarito", "Gabarito de janeiro")]
NATUREZAS = {"V": "Variável", "D": "Derivado", "F": "Fixo"}


def _caso(db: Session, id: int) -> Caso | None:
    return db.get(Caso, id)


def _ctx(caso: Caso, aba: str, **kw):
    return {"caso": caso, "aba": aba, "abas": ABAS, "menu": "casos", "escopos": ESCOPOS, "naturezas": NATUREZAS, **kw}


def _txt(form, k):
    v = (form.get(k) or "").strip()
    return v or None


def _volta(form, padrao: str) -> str:
    v = form.get("volta") or padrao
    return v if v.startswith("/") else padrao


# ======================================================================= casos
@router.get("/casos")
def lista(request: Request, db: Session = Depends(get_db)):
    casos = db.scalars(select(Caso).order_by(Caso.id)).all()
    if not casos:  # primeira visita: já deixa o caso-base carregado
        carregar_caso_base(db)
        db.commit()
        casos = db.scalars(select(Caso).order_by(Caso.id)).all()
    c = request.state.usuario
    if c and "professor" in c.perfis and not c.gestor and "visitante" not in c.perfis:
        casos = [k for k in casos if k.docente_id is None or k.docente_id == c.docente_id]  # caso-base + a própria cópia
    docentes = db.scalars(select(Docente).order_by(Docente.nome)).all()
    return render(request, "casos/lista.html", casos=casos, docentes=docentes, menu="casos")


def _docente_permitido(request: Request, form) -> int | None:
    """Coordenação escolhe o professor responsável; o professor só cria/edita cópias em seu próprio nome."""
    c = request.state.usuario
    if c and not c.gestor:
        return c.docente_id
    return int(form["docente_id"]) if (form.get("docente_id") or "").isdigit() else None


@router.post("/casos/carregar")
async def carregar_base(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    caso = carregar_caso_base(db, _txt(form, "nome") or "EH0012 · Caso-base 2026.2", num(form.get("docente_id")) and int(form["docente_id"]))
    db.commit()
    return voltar(f"/casos/{caso.id}/empresa", "Caso-base carregado.")


@router.post("/casos/importar")
async def importar_json(request: Request, arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        dados = json.loads((await arquivo.read()).decode("utf-8"))
        caso = importar(db, dados, None)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return voltar("/casos", erro=f"Arquivo inválido: {e}")
    return voltar(f"/casos/{caso.id}/empresa", "Caso importado.")


@router.post("/casos/{id}/duplicar")
async def duplicar_caso(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    origem = _caso(db, id)
    docente_id = _docente_permitido(request, form)
    novo = duplicar(db, origem, _txt(form, "nome") or f"{origem.nome} (cópia)", docente_id)
    db.commit()
    return voltar(f"/casos/{novo.id}/empresa", "Cópia criada. As alterações aqui não afetam o caso de origem.")


@router.post("/casos/{id}/editar")
async def editar_caso(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    caso.nome = _txt(form, "nome") or caso.nome
    caso.descricao = _txt(form, "descricao")
    caso.docente_id = _docente_permitido(request, form)
    db.commit()
    return voltar(_volta(form, f"/casos/{id}/empresa"), "Dados do caso salvos.")


@router.post("/casos/{id}/excluir")
def excluir_caso(id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    if caso:
        db.delete(caso)
        db.commit()
    return voltar("/casos", "Caso excluído.")


@router.get("/casos/{id}/exportar")
def exportar_caso(id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    corpo = json.dumps(exportar(caso), ensure_ascii=False, indent=2, default=str)
    nome = "".join(c if c.isalnum() else "_" for c in caso.nome)[:60]
    return Response(corpo, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="caso_{nome}.json"'})


@router.get("/casos/{id}")
def abrir(id: int):
    return voltar(f"/casos/{id}/empresa")


# ================================================================== parâmetros
@router.post("/casos/{id}/parametros")
async def salvar_parametros(request: Request, id: int, db: Session = Depends(get_db)):
    """Salva em lote as linhas de uma tabela de parâmetros (qualquer tela)."""
    form = await request.form()
    caso = _caso(db, id)
    avisos = []
    por_id = {p.id: p for p in caso.parametros}
    for pid in form.getlist("pid"):
        p = por_id.get(int(pid))
        if not p:
            continue
        if form.get(f"x_{pid}"):
            db.delete(p)
            continue
        p.nome = _txt(form, f"nome_{pid}") or p.nome
        p.unidade = _txt(form, f"unidade_{pid}")
        p.base = _txt(form, f"base_{pid}")
        p.minimo, p.maximo, p.passo = (num(form.get(f"min_{pid}")), num(form.get(f"max_{pid}")),
                                       num(form.get(f"passo_{pid}")))
        p.regra = _txt(form, f"regra_{pid}")
        p.varia = form.get(f"varia_{pid}") == "on"
        if p.minimo is not None and p.maximo is not None and p.minimo > p.maximo:
            p.minimo, p.maximo = p.maximo, p.minimo
            avisos.append(f"“{p.nome}”: mínimo e máximo estavam invertidos e foram trocados.")
        b = num(p.base)
        if b is not None and p.minimo is not None and p.maximo is not None and not (p.minimo <= b <= p.maximo) \
                and (p.unidade or "R$") not in ("% sobre a base", "% do salário"):
            avisos.append(f"“{p.nome}”: o valor base ({p.base}) está fora da faixa.")
        if p.passo is not None and p.passo <= 0:
            p.passo = None
            avisos.append(f"“{p.nome}”: passo deve ser maior que zero (removido).")
    # nova linha
    if _txt(form, "novo_nome"):
        maior = max([p.ordem for p in caso.parametros] or [0])
        caso.parametros.append(Parametro(
            escopo=form.get("escopo") or "empresa", ref=form.get("ref") or "", nome=form["novo_nome"].strip(),
            unidade=_txt(form, "novo_unidade"), base=_txt(form, "novo_base"), minimo=num(form.get("novo_min")),
            maximo=num(form.get("novo_max")), passo=num(form.get("novo_passo")), regra=_txt(form, "novo_regra"),
            varia=form.get("novo_varia") == "on", ordem=maior + 1))
    db.commit()
    url = _volta(form, f"/casos/{id}/empresa")
    return voltar(url, "Parâmetros salvos." + (" " + " ".join(avisos) if avisos else ""))


# =========================================================== edição genérica
def _salvar_tabela(form, prefixo: str, registros: list, novo, campos: dict, db: Session):
    """campos = {coluna: 'txt'|'num'|'int'}; linhas: {prefixo}_{campo}_{id}; nova linha: {prefixo}_{campo}_novo."""
    conv = {"txt": lambda v: (v or "").strip() or None, "num": num,
            "int": lambda v: int(num(v)) if num(v) is not None else None}
    for r in registros:
        if form.get(f"{prefixo}_x_{r.id}"):
            db.delete(r)
            continue
        for c, t in campos.items():
            k = f"{prefixo}_{c}_{r.id}"
            if k in form:
                setattr(r, c, conv[t](form.get(k)))
    primeiro = next(iter(campos))
    if (form.get(f"{prefixo}_{primeiro}_novo") or "").strip():
        obj = novo()
        for c, t in campos.items():
            setattr(obj, c, conv[t](form.get(f"{prefixo}_{c}_novo")))
        return obj
    return None


def _salvar_lista_json(form, prefixo: str, linhas: list[dict], colunas: list[str]) -> list[dict]:
    out = []
    for i, linha in enumerate(linhas):
        if form.get(f"{prefixo}_x_{i}"):
            continue
        nova = dict(linha)
        for c in colunas:
            v = (form.get(f"{prefixo}_{c}_{i}") or "").strip()
            n = num(v)
            nova[c] = n if (n is not None and isinstance(linha.get(c), (int, float))) else (v or None)
        out.append(nova)
    if (form.get(f"{prefixo}_{colunas[0]}_novo") or "").strip():
        nova = {}
        for c in colunas:
            v = (form.get(f"{prefixo}_{c}_novo") or "").strip()
            nova[c] = num(v) if num(v) is not None and c not in ("bem", "classe", "item", "ncm", "aquisicao") else (v or None)
        out.append(nova)
    return out


# ============================================================ empresa e sócios
@router.get("/casos/{id}/empresa")
def aba_empresa(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    if not caso:
        return voltar("/casos", erro="Caso não encontrado.")
    docentes = db.scalars(select(Docente).order_by(Docente.nome)).all()
    return render(request, "casos/empresa.html", **_ctx(caso, "empresa", docentes=docentes))


@router.post("/casos/{id}/empresa")
async def salvar_empresa(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    dados = dict(caso.dados or {})
    secao = form.get("secao")
    if secao == "empresa":
        emp = {}
        for k in (dados.get("empresa") or {}):
            emp[k] = (form.get(f"emp_{k}") or "").strip()
        if _txt(form, "emp_novo_chave"):
            emp[form["emp_novo_chave"].strip()] = (form.get("emp_novo_valor") or "").strip()
        for k in list(emp):
            if form.get(f"emp_x_{k}"):
                emp.pop(k)
        dados["empresa"] = emp
    elif secao in ("imobilizado", "vida_util", "rateio_areas"):
        colunas = {"imobilizado": ["bem", "ncm", "aquisicao", "valor", "taxa_fiscal_aa", "classe", "vida_util_anos", "residual_pct"],
                   "vida_util": ["classe", "anos", "residual_pct"],
                   "rateio_areas": ["item", "adm", "com", "ind"]}[secao]
        dados[secao] = _salvar_lista_json(form, secao, dados.get(secao) or [], colunas)
    elif secao == "socios":
        novo = _salvar_tabela(form, "s", list(caso.socios), Socio, {
            "nome": "txt", "funcao": "txt", "cotas": "int", "a_integralizar": "num", "evento_integralizacao": "txt",
            "pro_labore_jan": "num", "pro_labore_fev": "num", "dependentes": "txt"}, db)
        if novo:
            caso.socios.append(novo)
    caso.dados = dados
    db.commit()
    return voltar(f"/casos/{id}/empresa#{secao}", "Alterações salvas.")


# ================================================================== contratos
@router.get("/casos/{id}/contratos")
def aba_contratos(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    return render(request, "casos/contratos.html", **_ctx(caso, "contratos"))


@router.post("/casos/{id}/contratos/novo")
async def novo_contrato(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    nums = [int(c.codigo[1:]) for c in caso.contratos if c.codigo[1:].isdigit()]
    cod = f"C{(max(nums or [0]) + 1):02d}"
    caso.contratos.append(Contrato(codigo=cod, tipo="Novo contrato", parte="", inicio=None))
    db.commit()
    return voltar(f"/casos/{id}/contratos#{cod}", f"Contrato {cod} criado. Preencha os dados e os parâmetros.")


@router.post("/casos/{id}/contratos/{cid}")
async def salvar_contrato(request: Request, id: int, cid: int, db: Session = Depends(get_db)):
    form = await request.form()
    c = db.get(Contrato, cid)
    caso = _caso(db, id)
    antigo = c.codigo
    c.codigo = (_txt(form, "codigo") or c.codigo).upper()
    c.tipo = _txt(form, "tipo") or c.tipo
    c.parte = _txt(form, "parte")
    c.inicio = date.fromisoformat(form["inicio"]) if form.get("inicio") else None
    c.descricao = _txt(form, "descricao")
    c.eventos = _txt(form, "eventos")
    if antigo != c.codigo:
        for p in caso.params("contrato", antigo):
            p.ref = c.codigo
    db.commit()
    return voltar(f"/casos/{id}/contratos#{c.codigo}", f"Contrato {c.codigo} salvo.")


@router.post("/casos/{id}/contratos/{cid}/excluir")
def excluir_contrato(id: int, cid: int, db: Session = Depends(get_db)):
    c = db.get(Contrato, cid)
    caso = _caso(db, id)
    if c:
        for p in caso.params("contrato", c.codigo):
            db.delete(p)
        db.delete(c)
        db.commit()
    return voltar(f"/casos/{id}/contratos", "Contrato excluído.")


# ======================================================================= folha
FUNC_CAMPOS = {"setor": "txt", "nome": "txt", "admissao": "txt", "salario_jan": "num", "he_jan": "num",
               "comissao_jan": "num", "dependentes_jan": "txt", "salario_fev": "num", "he_fev": "num",
               "comissao_fev": "num", "dependentes_fev": "txt"}


@router.get("/casos/{id}/folha")
def aba_folha(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    fs = caso.funcionarios
    tot = {"jan": sum(1 for f in fs if f.salario_jan), "fev": sum(1 for f in fs if f.salario_fev or f.admissao),
           "massa_jan": sum(f.salario_jan or 0 for f in fs), "massa_fev": sum(f.salario_fev or 0 for f in fs)}
    return render(request, "casos/folha.html", **_ctx(caso, "folha", tot=tot))


@router.post("/casos/{id}/folha")
async def salvar_folha(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    secao = form.get("secao")
    if secao == "regras":
        dados = dict(caso.dados or {})
        regras = {}
        for k in (dados.get("folha_regras") or {}):
            if not form.get(f"reg_x_{k}"):
                regras[k] = (form.get(f"reg_{k}") or "").strip()
        if _txt(form, "reg_novo_chave"):
            regras[form["reg_novo_chave"].strip()] = (form.get("reg_novo_valor") or "").strip()
        dados["folha_regras"] = regras
        caso.dados = dados
    else:
        novo = _salvar_tabela(form, "f", list(caso.funcionarios), Funcionario, FUNC_CAMPOS, db)
        if novo:
            novo.ordem = max([f.ordem for f in caso.funcionarios] or [0]) + 1
            caso.funcionarios.append(novo)
    db.commit()
    return voltar(f"/casos/{id}/folha#{secao}", "Alterações salvas.")


# ==================================================================== produção
@router.get("/casos/{id}/producao")
def aba_producao(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    produtos = [i for i in caso.itens if i.tipo == "Produto acabado"]
    insumos = [i for i in caso.itens if i.tipo in ("Matéria-prima", "Material secundário", "Embalagem")]
    ficha = {(f.produto, f.insumo): f.quantidade for f in caso.ficha}
    plano = (caso.dados or {}).get("plano_producao", {})
    # necessidade de insumos pelo plano base
    necessidade = {}
    for ins in insumos:
        necessidade[ins.codigo] = sum((ficha.get((p.codigo, ins.codigo)) or 0) * (num(plano.get(p.codigo)) or 0)
                                      for p in produtos)
    return render(request, "casos/producao.html", **_ctx(caso, "producao", produtos=produtos, insumos=insumos,
                                                          ficha=ficha, plano=plano, necessidade=necessidade))


@router.post("/casos/{id}/producao")
async def salvar_producao(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    secao = form.get("secao")
    if secao == "itens":
        novo = _salvar_tabela(form, "i", list(caso.itens), Item, {
            "codigo": "txt", "descricao": "txt", "tipo": "txt", "ncm": "txt", "custo_base": "num",
            "custo_min": "num", "custo_max": "num"}, db)
        if novo:
            novo.ordem = max([i.ordem for i in caso.itens] or [0]) + 1
            caso.itens.append(novo)
    elif secao == "ficha":
        atual = {(f.produto, f.insumo): f for f in caso.ficha}
        for k, v in form.multi_items():
            if not k.startswith("ft|"):
                continue
            _, prod, ins = k.split("|")
            q = num(v)
            f = atual.get((prod, ins))
            if q in (None, 0):
                if f:
                    db.delete(f)
            elif f:
                f.quantidade = q
            else:
                caso.ficha.append(FichaTecnica(produto=prod, insumo=ins, quantidade=q))
    elif secao in ("plano", "markup"):
        dados = dict(caso.dados or {})
        chave = "plano_producao" if secao == "plano" else "markup"
        bloco = {}
        for k, v0 in (dados.get(chave) or {}).items():
            v = (form.get(f"{secao}_{k}") or "").strip()
            bloco[k] = num(v) if isinstance(v0, (int, float)) and num(v) is not None else v
        dados[chave] = bloco
        caso.dados = dados
    db.commit()
    return voltar(f"/casos/{id}/producao#{secao}", "Alterações salvas.")


# ===================================================================== eventos
@router.get("/casos/{id}/eventos")
def aba_eventos(request: Request, id: int, mes: str = "", natureza: str = "", q: str = "",
                db: Session = Depends(get_db)):
    caso = _caso(db, id)
    evs = caso.eventos
    if mes:
        evs = [e for e in evs if e.data and e.data.strftime("%Y-%m") == mes]
    if natureza:
        evs = [e for e in evs if e.natureza == natureza]
    if q:
        ql = q.lower()
        evs = [e for e in evs if ql in (e.descricao or "").lower() or ql in e.codigo.lower() or ql in (e.grupo or "").lower()]
    nparams = {}
    for p in caso.parametros:
        if p.escopo == "evento":
            nparams[p.ref] = nparams.get(p.ref, 0) + 1
    meses = sorted({e.data.strftime("%Y-%m") for e in caso.eventos if e.data})
    return render(request, "casos/eventos.html", **_ctx(caso, "eventos", evs=evs, mes=mes, natureza=natureza, q=q,
                                                         nparams=nparams, meses=meses))


@router.get("/casos/{id}/eventos/{eid}")
def editar_evento(request: Request, id: int, eid: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    e = db.get(Evento, eid)
    if not e or e.caso_id != id:
        return voltar(f"/casos/{id}/eventos", erro="Evento não encontrado.")
    lista = caso.eventos
    i = lista.index(e)
    return render(request, "casos/evento.html", **_ctx(caso, "eventos", e=e,
                                                        anterior=lista[i - 1] if i > 0 else None,
                                                        proximo=lista[i + 1] if i + 1 < len(lista) else None))


@router.post("/casos/{id}/eventos/novo")
async def novo_evento(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    d = date.fromisoformat(form.get("data") or "2026-01-02")
    pre = {1: "J", 2: "F"}.get(d.month, "E")
    nums = [int(e.codigo[1:]) for e in caso.eventos if e.codigo.startswith(pre) and e.codigo[1:].isdigit()]
    e = Evento(codigo=f"{pre}{(max(nums or [0]) + 1):02d}", data=d, grupo="", descricao="Novo evento", natureza="V")
    caso.eventos.append(e)
    db.commit()
    return voltar(f"/casos/{id}/eventos/{e.id}", f"Evento {e.codigo} criado.")


@router.post("/casos/{id}/eventos/{eid}")
async def salvar_evento(request: Request, id: int, eid: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    e = db.get(Evento, eid)
    antigo = e.codigo
    e.codigo = (_txt(form, "codigo") or e.codigo).upper()
    e.data = date.fromisoformat(form["data"]) if form.get("data") else e.data
    e.grupo = _txt(form, "grupo")
    e.descricao = _txt(form, "descricao") or e.descricao
    e.natureza = form.get("natureza") if form.get("natureza") in NATUREZAS else e.natureza
    e.contrato = _txt(form, "contrato")
    e.obs = _txt(form, "obs")
    if antigo != e.codigo:
        for p in caso.params("evento", antigo):
            p.ref = e.codigo
    db.commit()
    return voltar(f"/casos/{id}/eventos/{eid}", f"Evento {e.codigo} salvo.")


@router.post("/casos/{id}/eventos/{eid}/excluir")
def excluir_evento(id: int, eid: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    e = db.get(Evento, eid)
    if e:
        for p in caso.params("evento", e.codigo):
            db.delete(p)
        db.delete(e)
        db.commit()
    return voltar(f"/casos/{id}/eventos", "Evento excluído.")


# ============================================================ inconsistências
@router.get("/casos/{id}/inconsistencias")
def aba_inconsistencias(request: Request, id: int, db: Session = Depends(get_db)):
    caso = _caso(db, id)
    return render(request, "casos/inconsistencias.html", **_ctx(caso, "inconsistencias"))


@router.post("/casos/{id}/inconsistencias")
async def salvar_inconsistencias(request: Request, id: int, db: Session = Depends(get_db)):
    form = await request.form()
    caso = _caso(db, id)
    novo = _salvar_tabela(form, "n", list(caso.inconsistencias), Inconsistencia,
                          {"onde": "txt", "descricao": "txt", "decisao": "txt", "status": "txt"}, db)
    if novo:
        novo.status = novo.status or "PENDENTE"
        caso.inconsistencias.append(novo)
    db.commit()
    return voltar(f"/casos/{id}/inconsistencias", "Decisões salvas.")
