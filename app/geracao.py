"""Geração da empresa de cada dupla a partir de um Caso.

Princípios (docs/PARAMETRIZACAO.md):
- datas, CFOPs e alíquotas ficam fixos; só os números variam, dentro da faixa [mínimo, máximo] e no passo definido;
- o sorteio é reproduzível: cada parâmetro usa um gerador próprio semeado por (semente da dupla, escopo, ref, nome),
  de modo que incluir/alterar um parâmetro não muda os demais valores já sorteados;
- quantidades derivadas seguem regras de coerência: compra = necessidade da ficha técnica × produção + sobra;
  vendas < produção; salários arredondados a R$ 10 e nunca abaixo do salário mínimo.
"""
from __future__ import annotations

import contextvars
import math
import random
import secrets

from .caso_servico import num
from .models_caso import Caso, Parametro

SALARIO_MINIMO = 1621.00  # 2026 (valor usado no caso-base)
# Parâmetros mantidos no valor-base porque estão presos ao balanço de 31/12/2025
# (ex.: o prêmio do seguro define os "Prêmios de seguros a apropriar" e a despesa de 2025 na DRE).
FIXOS_SALDO = {("contrato", "C09")}
# Evento de compra de cada insumo: o custo unitário sorteado no evento é o custo do insumo.
EVENTO_INSUMO = {"MP-A": "J30", "MP-B": "F05", "ME-H": "F22"}
EVENTO_DEVOLUCAO = {"MP-A": "F28"}
FORMATO = "labcont-empresa/1"


# Modo "caso-base": todos os parâmetros no valor de referência (para conferir o gabarito do exercício original)
_MODO_BASE: contextvars.ContextVar[bool] = contextvars.ContextVar("modo_base", default=False)


def nova_semente() -> int:
    return secrets.randbelow(2_000_000_000) + 1


def _rng(semente: int, *chave) -> random.Random:
    return random.Random("|".join([str(semente), *map(str, chave)]))


def _casas(passo: float | None) -> int:
    if not passo:
        return 2
    s = f"{passo:.6f}".rstrip("0")
    return max(0, len(s.split(".")[1])) if "." in s else 0


def sortear_faixa(rng: random.Random, minimo: float, maximo: float, passo: float | None) -> float:
    """Valor uniforme em [mínimo, máximo], múltiplo do passo a partir do mínimo."""
    if maximo < minimo:
        minimo, maximo = maximo, minimo
    if passo and passo > 0 and passo <= (maximo - minimo):
        k = rng.randint(0, int(math.floor((maximo - minimo) / passo + 1e-9)))
        casas = _casas(passo)
        v = round(minimo + k * passo, casas)
        return int(v) if casas == 0 and float(minimo).is_integer() else v
    if passo and passo > 0:  # passo maior que a faixa: só os extremos
        return rng.choice([minimo, maximo])
    return round(rng.uniform(minimo, maximo), 2)


def sortear_parametro(semente: int, p: Parametro, *extra) -> float | str | None:
    if _MODO_BASE.get():
        v = num(p.base)
        return v if v is not None else p.base
    if p.varia and p.minimo is not None and p.maximo is not None:
        return sortear_faixa(_rng(semente, p.escopo, p.ref or "", p.nome, *extra), p.minimo, p.maximo, p.passo)
    v = num(p.base)
    return v if v is not None else p.base


def _achar(caso: Caso, escopo: str, *trechos: str) -> Parametro | None:
    for p in caso.params(escopo):
        nome = p.nome.lower()
        if all(t.lower() in nome for t in trechos):
            return p
    return None


def _ap10(v: float) -> float:
    return float(round(v / 10.0) * 10)


# ------------------------------------------------------------------ blocos derivados
def _param_evento(caso: Caso, ref: str, trecho: str) -> Parametro | None:
    for p in caso.params("evento", ref):
        if trecho.lower() in p.nome.lower():
            return p
    return None


def _qtd_base_compra(caso: Caso, cod: str) -> int | None:
    ref = EVENTO_INSUMO.get(cod)
    if ref:
        p = _param_evento(caso, ref, "quantidade")
        return int(num(p.base)) if p is not None and num(p.base) else None
    p = _param_evento(caso, "F10", "quantidades")
    ordem = ["MS-Z", "MS-Q", "MS-R", "MS-K"]
    if p is not None and cod in ordem and p.base:
        partes = [num(x) for x in str(p.base).split("/")]
        i = ordem.index(cod)
        return int(partes[i]) if i < len(partes) and partes[i] else None
    return None


def _producao(caso: Caso, semente: int, valores: dict[int, object]) -> dict:
    itens = {i.codigo: i for i in caso.itens}
    produtos = [i.codigo for i in caso.itens if (i.tipo or "").lower().startswith("produto")]
    plano = (caso.dados or {}).get("plano_producao", {}) or {}
    p_coef = _achar(caso, "producao", "coeficiente")
    p_sobra = _achar(caso, "producao", "sobra")
    p_vend = _achar(caso, "producao", "vendido")
    p_custo = _achar(caso, "producao", "custo unit")

    saida_prod = []
    for cod in produtos:
        p_q = _achar(caso, "producao", "quantidade produzida", f"produto {cod}")
        q = sortear_parametro(semente, p_q) if p_q else num(plano.get(cod))
        q = int(q or 0)
        pct = sortear_parametro(semente, p_vend, cod) if p_vend else 100.0
        pct = num(pct) if num(pct) is not None else 100.0
        vendido = min(q - 1, int(math.floor(q * pct / 100.0))) if q else 0
        p_vb = _param_evento(caso, "F34", f"vendida {cod}") if _MODO_BASE.get() else None
        if p_vb is not None and num(p_vb.base):
            vendido = int(num(p_vb.base))
            pct = round(vendido / q * 100, 2) if q else pct
        saida_prod.append({"codigo": cod, "descricao": itens[cod].descricao, "quantidade": q,
                           "pct_vendido": pct, "vendido": max(vendido, 0), "estoque_final": q - max(vendido, 0)})
    qtd = {p["codigo"]: p["quantidade"] for p in saida_prod}

    coef: dict[tuple[str, str], float] = {}
    for f in caso.ficha:
        c = f.quantidade
        tipo = (itens[f.insumo].tipo if f.insumo in itens else "").lower()
        if p_coef and p_coef.varia and p_coef.minimo is not None and "embalagem" not in tipo and not _MODO_BASE.get():
            d = _rng(semente, "ficha", f.produto, f.insumo).randint(int(p_coef.minimo), int(p_coef.maximo))
            c = max(1.0, c + d)
        coef[(f.produto, f.insumo)] = c

    insumos = []
    for i in caso.itens:
        usos = {prod: coef[(prod, i.codigo)] for prod in produtos if (prod, i.codigo) in coef}
        if not usos:
            continue
        necessidade = int(sum(c * qtd.get(prod, 0) for prod, c in usos.items()))
        sobra = int(num(sortear_parametro(semente, p_sobra, i.codigo)) or 0) if p_sobra else 0
        p_ev = _param_evento(caso, EVENTO_INSUMO.get(i.codigo, ""), "custo unit")
        if p_ev is not None and num(valores.get(p_ev.id)) is not None:
            custo = num(valores.get(p_ev.id))
        elif p_custo and p_custo.varia and i.custo_min is not None and i.custo_max is not None and not _MODO_BASE.get():
            custo = round(_rng(semente, "custo", i.codigo).uniform(i.custo_min, i.custo_max), 4)
        else:
            custo = i.custo_base
        p_dev = _param_evento(caso, EVENTO_DEVOLUCAO.get(i.codigo, ""), "devolvida")
        devolucao = int(num(valores.get(p_dev.id)) or 0) if p_dev is not None else 0
        compra = necessidade + sobra + devolucao
        if _MODO_BASE.get():  # caso-base: quantidade comprada informada no exercício
            qb = _qtd_base_compra(caso, i.codigo)
            if qb:
                compra, sobra = qb, qb - necessidade - devolucao
        insumos.append({"codigo": i.codigo, "descricao": i.descricao, "tipo": i.tipo, "por_produto": usos,
                        "necessidade": necessidade, "sobra": sobra, "devolucao": devolucao, "compra": compra, "custo_unit": custo,
                        "valor_compra": round(compra * (custo or 0), 2)})
    return {"produtos": saida_prod, "insumos": insumos,
            "total_compras": round(sum(x["valor_compra"] for x in insumos), 2)}


def _folha(caso: Caso, semente: int) -> list[dict]:
    p_sal = _achar(caso, "folha", "salário")
    p_he = _achar(caso, "folha", "horas extras")
    p_com = _achar(caso, "folha", "comiss")
    out = []
    for f in caso.funcionarios:
        chave = f.nome
        fator = 1.0
        if p_sal and p_sal.varia and p_sal.minimo is not None and not _MODO_BASE.get():
            fator = 1 + float(sortear_parametro(semente, p_sal, chave)) / 100.0

        def sal(v):
            return None if v is None else max(SALARIO_MINIMO, _ap10(v * fator))
        sj, sf = sal(f.salario_jan), sal(f.salario_fev)

        def extra(base, novo_sal, p, rotulo):
            if not base or novo_sal is None:
                return None
            if p and p.varia and p.minimo is not None and not _MODO_BASE.get():
                pct = max(2.0, float(sortear_parametro(semente, p, chave, rotulo)))
                return round(novo_sal * pct / 100.0, 2)
            return base
        out.append({"setor": f.setor, "nome": f.nome, "admissao": f.admissao,
                    "salario_jan": sj, "he_jan": extra(f.he_jan, sj, p_he, "jan"),
                    "comissao_jan": extra(f.comissao_jan, sj, p_com, "jan"), "dependentes_jan": f.dependentes_jan,
                    "salario_fev": sf, "he_fev": extra(f.he_fev, sf, p_he, "fev"),
                    "comissao_fev": extra(f.comissao_fev, sf, p_com, "fev"), "dependentes_fev": f.dependentes_fev,
                    "pendente": f.salario_fev is None and f.salario_jan is None})
    return out


def _markup(caso: Caso, valores: dict[int, object]) -> dict:
    m = dict((caso.dados or {}).get("markup", {}) or {})
    pm = caso.params("markup")
    margem = num(valores.get(pm[0].id)) if pm else num(m.get("margem_contribuicao"))
    trib = sum(num(m.get(k)) or 0 for k in ("ICMS", "PIS", "COFINS"))
    if margem is None:
        return m
    divisor = round(1 - (trib + margem) / 100.0, 4)
    return {**m, "margem_contribuicao": margem, "divisor": divisor,
            "multiplicador": round(1 / divisor, 4) if divisor > 0 else None}


def _coerencia_estoque(caso: Caso, valores: dict[int, object]) -> set[int]:
    """Vendas de mercadoria (ALPHA) não podem superar estoque inicial + compras (custo médio móvel).
    Se o sorteio ultrapassar, reduz a última venda (F26) e, se preciso, a primeira (J27), no passo do parâmetro."""
    import re as _re
    ini = 0
    for k in ((caso.dados or {}).get("saldos_iniciais", {}) or {}).get("ativo", {}) or {}:
        m = _re.search(r"ALPHA \((\d+) un", k)
        if m:
            ini = int(m.group(1))
    compra = _param_evento(caso, "J15", "quantidade")
    vendas = [_param_evento(caso, "J27", "quantidade"), _param_evento(caso, "F04", "quantidade"),
              _param_evento(caso, "F26", "quantidade")]
    if compra is None or any(v is None for v in vendas):
        return set()
    disp = ini + int(num(valores[compra.id]) or 0)
    total = sum(int(num(valores[v.id]) or 0) for v in vendas)
    ajustados = set()
    for v in (vendas[2], vendas[0]):
        if total <= disp:
            break
        atual = int(num(valores[v.id]) or 0)
        passo = int(v.passo or 1)
        novo = max(0, atual - (total - disp))
        novo = (novo // passo) * passo
        valores[v.id] = novo
        total -= atual - novo
        ajustados.add(v.id)
    return ajustados


# ------------------------------------------------------------------ geração
def gerar(caso: Caso, semente: int, rotulo: str = "", numero: int | None = None, base: bool = False) -> dict:
    token = _MODO_BASE.set(base)
    try:
        v = _gerar(caso, semente, rotulo, numero)
    finally:
        _MODO_BASE.reset(token)
    if base:
        v["modo"] = "caso-base"
    return v


def _gerar(caso: Caso, semente: int, rotulo: str = "", numero: int | None = None) -> dict:
    fixo = {p.id for p in caso.parametros if (p.escopo, p.ref or "") in FIXOS_SALDO}
    valores = {p.id: (num(p.base) if num(p.base) is not None else p.base) if p.id in fixo
               else sortear_parametro(semente, p) for p in caso.parametros}
    ajustados = _coerencia_estoque(caso, valores)
    parametros = [{
        "escopo": p.escopo, "ref": p.ref or "", "nome": p.nome, "unidade": p.unidade, "base": p.base,
        "ajustado": p.id in ajustados, "min": p.minimo, "max": p.maximo, "passo": p.passo, "varia": p.varia and p.id not in fixo,
        "valor": valores[p.id], "regra": p.regra,
    } for p in caso.parametros]
    emp = dict((caso.dados or {}).get("empresa", {}) or {})
    nome_base = emp.get("nome") or "Empresa LAB"
    if numero is not None:
        emp["nome"] = f"{nome_base} {numero:02d}"
    socios = []
    p_cap = _achar(caso, "empresa", "capital social")
    base_cotas = sum(s.cotas or 0 for s in caso.socios)
    capital = int(num(valores.get(p_cap.id)) or base_cotas) if p_cap else base_cotas
    nomes_pl = {"administra": "administrador", "comerc": "comercial", "industri": "industrial"}
    for s in caso.socios:
        pl = None
        for chave, termo in nomes_pl.items():
            if chave in (s.funcao or "").lower():
                p = _achar(caso, "socios", "pró-labore", termo)
                pl = valores.get(p.id) if p else None
        cotas = int(round(capital * (s.cotas or 0) / base_cotas)) if base_cotas else s.cotas
        if s.cotas and s.a_integralizar is not None:
            a_int = float(cotas) if s.a_integralizar >= s.cotas else float(round(cotas * s.a_integralizar / s.cotas, -3))
        else:
            a_int = s.a_integralizar
        socios.append({"nome": s.nome, "funcao": s.funcao, "cotas": cotas, "a_integralizar": a_int, "dependentes": s.dependentes,
                       "pro_labore_jan": pl if (pl is not None and s.pro_labore_jan) else s.pro_labore_jan,
                       "pro_labore_fev": pl if (pl is not None and s.pro_labore_fev) else s.pro_labore_fev})
    if socios and base_cotas:  # ajusta arredondamento: soma das cotas = capital
        maior = max(socios, key=lambda x: x["cotas"] or 0)
        maior["cotas"] += capital - sum(x["cotas"] or 0 for x in socios)
    producao = _producao(caso, semente, valores)
    folha = _folha(caso, semente)
    variados = [x for x in parametros if x["varia"] and x["min"] is not None]
    return {
        "formato": FORMATO, "semente": semente, "dupla": rotulo,
        "caso": {"id": caso.id, "nome": caso.nome},
        "empresa": emp, "capital_social": capital, "parametros": parametros, "socios": socios,
        "producao": producao, "folha": folha, "markup": _markup(caso, valores),
        "resumo": {
            "parametros_sorteados": len(variados),
            "producao_total": sum(p["quantidade"] for p in producao["produtos"]),
            "total_compras_insumos": producao["total_compras"],
            "folha_fev": round(sum((f["salario_fev"] or 0) for f in folha), 2),
            "empregados_fev": sum(1 for f in folha if f["salario_fev"] is not None or f["pendente"]),
        },
        "pendencias": ["Balanço de abertura e lançamentos dos eventos: gerados na etapa de documentos digitais "
                       "(o saldo do Banco Rico fecha a equação patrimonial)."]
                      + [f"Salário de {f['nome']} sem valor no caso — decidir na aba Inconsistências."
                         for f in folha if f["pendente"]],
    }
