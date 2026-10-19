"""Documento de orientação (.docx) da dupla, no mesmo formato do exercício-base.

O arquivo-modelo é o próprio exercício EH0012 (dados/caso_base/modelo_orientacao_eh0012.docx).
Cada regra abaixo localiza um trecho do texto (âncora) e troca o valor-base pelo valor sorteado
para a dupla, preservando a formatação original (fonte, tabelas, cabeçalho e índice).
Valores derivados que aparecem no texto (totais de notas, consumo em kWh/m³, ICMS e multa do auto,
destinação do lucro, balanço de abertura) são recalculados para manter o documento coerente.
"""
from __future__ import annotations

import copy
import io
import re
from pathlib import Path

from docx import Document
from num2words import num2words

from .caso_servico import fmt, num
from .config import BASE_DIR
from .models import normalizar

MODELO = BASE_DIR / "dados" / "caso_base" / "modelo_orientacao_eh0012.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


# ------------------------------------------------------------------ formatação
def brl(v) -> str:
    return fmt(round(float(v), 2), 2)


def inteiro(v) -> str:
    return fmt(int(round(float(v))), 0)


def pct(v, casas=None) -> str:
    v = float(v)
    if casas is None:
        casas = 0 if v.is_integer() else (1 if round(v, 1) == v else 2)
    return fmt(v, casas)


def extenso(v: float) -> str:
    return num2words(int(round(v)), lang="pt_BR")


# ------------------------------------------------------------------ texto no XML
def _ts(p) -> list:
    """Nós w:t que pertencem a este parágrafo (exclui parágrafos aninhados em caixas de texto)."""
    out = []
    for t in p.iter(W + "t"):
        anc = t.getparent()
        while anc is not None and anc.tag != W + "p":
            anc = anc.getparent()
        if anc is p:
            out.append(t)
    return out


def texto(p) -> str:
    return "".join(t.text or "" for t in _ts(p))


def _substituir_em(p, ini: int, fim: int, novo: str) -> None:
    pos = 0
    primeiro = True
    for t in _ts(p):
        s = t.text or ""
        a, b = pos, pos + len(s)
        pos = b
        if b <= ini or a >= fim:
            continue
        i0, i1 = max(ini - a, 0), min(fim - a, len(s))
        t.text = s[:i0] + (novo if primeiro else "") + s[i1:]
        t.set(XML_SPACE, "preserve")
        primeiro = False


def trocar(p, velho: str | re.Pattern, novo, limite: int = 0) -> int:
    """Troca ocorrências (texto ou regex) no parágrafo. `novo` pode ser função do match."""
    txt = texto(p)
    padrao = velho if isinstance(velho, re.Pattern) else re.compile(re.escape(velho))
    ms = list(padrao.finditer(txt))
    if limite:
        ms = ms[:limite]
    for m in reversed(ms):
        _substituir_em(p, m.start(), m.end(), novo(m) if callable(novo) else novo)
    return len(ms)


def definir(cel, novo: str) -> None:
    """Substitui todo o texto de uma célula/parágrafo, mantendo a formatação do primeiro trecho."""
    ts = list(cel.iter(W + "t"))
    if not ts:
        ps = list(cel.iter(W + "p"))
        if not ps:
            return
        r = ps[0].makeelement(W + "r", {})
        t = r.makeelement(W + "t", {})
        r.append(t)
        ps[0].append(r)
        ts = [t]
    ts[0].text = novo
    ts[0].set(XML_SPACE, "preserve")
    for t in ts[1:]:
        t.text = ""


class Doc:
    def __init__(self, caminho: Path):
        self.doc = Document(str(caminho))
        self.body = self.doc.element.body
        # ignora o índice (sumário automático, dentro de w:sdt)
        self.ps = [p for p in self.body.iter(W + "p") if not any(a.tag == W + "sdt" for a in p.iterancestors())]
        self.avisos: list[str] = []

    def achar(self, ancora: str, depois=None):
        ok = depois is None
        for p in self.ps:
            if not ok:
                ok = p is depois
                continue
            if ancora in texto(p):
                return p
        self.avisos.append(f"trecho não encontrado: “{ancora[:60]}”")
        return None

    def trocar(self, ancora: str, velho, novo, limite: int = 0, depois=None) -> None:
        p = self.achar(ancora, depois)
        if p is not None and not trocar(p, velho, novo, limite):
            self.avisos.append(f"valor “{velho if isinstance(velho, str) else velho.pattern}” não encontrado em “{ancora[:40]}”")

    def tabela_apos(self, ancora: str):
        p = self.achar(ancora)
        if p is None:
            return None
        el = p
        while el is not None and el.getparent() is not self.body:
            el = el.getparent()
        while el is not None:
            el = el.getnext()
            if el is not None and el.tag == W + "tbl":
                return [tr.findall(W + "tc") for tr in el.iter(W + "tr")]
        return None


def _linha(linhas, *trechos):
    for cels in linhas or []:
        t = normalizar("".join(x.text or "" for x in cels[0].iter(W + "t"))) if cels else ""
        if all(normalizar(x) in t for x in trechos):
            return cels
    return None


def _txt(cel) -> str:
    return "".join(x.text or "" for x in cel.iter(W + "t"))


# ------------------------------------------------------------------ valores da empresa
class Valores:
    def __init__(self, v: dict):
        self.v = v
        self.idx = {}
        for p in v.get("parametros", []):
            self.idx.setdefault((p["escopo"], p["ref"]), []).append(p)

    def p(self, escopo: str, ref: str, trecho: str, padrao=None):
        for p in self.idx.get((escopo, ref), []):
            if trecho.lower() in p["nome"].lower():
                val = num(p["valor"]) if not isinstance(p["valor"], (int, float)) else p["valor"]
                return padrao if val is None else val
        return padrao

    def base(self, escopo: str, ref: str, trecho: str):
        for p in self.idx.get((escopo, ref), []):
            if trecho.lower() in p["nome"].lower():
                return num(p["base"])
        return None

    def insumo(self, cod: str) -> dict:
        return next((i for i in self.v["producao"]["insumos"] if i["codigo"] == cod), {})

    def produto(self, cod: str) -> dict:
        return next((i for i in self.v["producao"]["produtos"] if i["codigo"] == cod), {})


# ------------------------------------------------------------------ seções do documento
def _capa(d: Doc, v: dict, rotulo: str) -> None:
    p = d.achar("Laboratório de Prática Contábil – ")
    if p is None:
        return
    nomes = " e ".join(m["nome"] for m in v.get("integrantes", []))
    for linha in reversed([f"{v['empresa'].get('nome', 'Empresa LAB')} · {rotulo}", nomes]):
        novo = copy.deepcopy(p)
        definir(novo, linha)
        for rpr in novo.iter(W + "sz"):
            rpr.set(W + "val", "24")
        p.addnext(novo)
    nome = v["empresa"].get("nome", "Empresa LAB").replace("Empresa ", "empresa ")
    for q in d.ps:
        if "empresa LAB " in texto(q):
            trocar(q, "empresa LAB ", nome + " ")


def _capital(d: Doc, v: dict) -> None:
    cap = float(v.get("capital_social") or 0)
    socios = v.get("socios", [])
    if not cap or not socios:
        return
    d.trocar("O Capital Social é de R$", re.compile(r"R\$ [\d.]+,\d\d \([^)]*\)"),
             f"R$ {brl(cap)} ({extenso(cap)} reais)", limite=1)
    d.trocar("O Capital Social é de R$", re.compile(r"divididos em [\d.]+ \([^)]*\)"),
             f"divididos em {inteiro(cap)} ({extenso(cap)})", limite=1)
    linhas = d.tabela_apos("O Capital Social é de R$")
    tot_int = 0.0
    for s in socios:
        cels = _linha(linhas, s["nome"])
        if not cels or len(cels) < 6:
            continue
        cotas, a_int = float(s["cotas"] or 0), float(s["a_integralizar"] or 0)
        tot_int += a_int
        definir(cels[1], inteiro(cotas))
        definir(cels[2], f"{brl(cotas / cap * 100)}%")
        definir(cels[3], brl(cotas))
        definir(cels[4], f"{brl((cotas - a_int) / cotas * 100) if cotas else '0,00'}%")
        definir(cels[5], f"{brl(a_int / cotas * 100) if cotas else '0,00'}%")
    cels = _linha(linhas, "Total")
    if cels and len(cels) >= 6:
        definir(cels[1], inteiro(cap))
        definir(cels[3], brl(cap))
        definir(cels[4], f"{brl((cap - tot_int) / cap * 100)}%")
        definir(cels[5], f"{brl(tot_int / cap * 100)}%")


def _destinacao(d: Doc, x: Valores) -> None:
    part = x.p("empresa", "", "participação de empregados")
    div = x.p("empresa", "", "dividendos")
    if part is not None:
        d.trocar("Distribuição de", re.compile(r"Distribuição de [\d,]+% do Lucro"), f"Distribuição de {pct(part)}% do Lucro")
    if div is not None:
        d.trocar("Dividendos –", re.compile(r"– [\d,]+% do Lucro"), f"– {pct(div)}% do Lucro")
    # quadro "Destinação do Lucro Líquido" (caixa de texto), recalculado
    lucro = 94923.97
    part_v = round(lucro * (part if part is not None else 8) / 100, 2)
    ll = round(lucro - part_v, 2)
    rl = round(ll * 0.05, 2)
    dv = round((ll - rl) * (div if div is not None else 50) / 100, 2)
    est = round(ll - rl - dv, 2)
    antigos = {"7.593,92": brl(part_v), "87.330,05": brl(ll), "4.366,50": brl(rl), "41.481,77": brl(dv), "41.481,78": brl(est)}
    for p in d.ps:
        t = texto(p)
        if t in antigos:
            trocar(p, t, antigos[t])


def _producao(d: Doc, x: Valores) -> None:
    for cod in ("X", "Y"):
        pr = x.produto(cod)
        if pr:
            d.trocar(f"Produto “{cod}” (NCM", re.compile(r"⇨\s*[\d.]+ unidades"), f"⇨{inteiro(pr['quantidade'])} unidades")
    # ficha técnica: "(MP-A) (NCM - 9002.11.11) 04 unidades" dentro do bloco de cada produto
    ini = d.achar("Ficha técnica dos produtos")
    atual, dentro = None, False
    for p in d.ps:
        if p is ini:
            dentro = True
            continue
        if not dentro:
            continue
        t = texto(p).strip()
        if t.startswith("Alocação dos custos"):
            break
        if t in ("Produto “X”", "Produto “Y”"):
            atual = t[-2]
            continue
        if atual is None:
            continue
        for ins in x.v["producao"]["insumos"]:
            c = ins["por_produto"].get(atual)
            if c is None:
                continue
            padrao = re.compile(r"(\(" + re.escape(ins["codigo"]) + r"\)\s*\(NCM - [\d.]+\)\s*)(\d+) unidades?")
            trocar(p, padrao, lambda m, c=c: f"{m.group(1)}{int(c):02d} {'unidade' if int(c) == 1 else 'unidades'}")
    margem = x.v.get("markup", {}).get("margem_contribuicao")
    if margem is not None:
        d.trocar("Margem de Contribuição –", re.compile(r"[\d,]+%"), f"{brl(margem)}%")


def _socios_prolabore(d: Doc, v: dict) -> None:
    func = {"adm": "administra", "comercial": "comerc", "industrial": "industri"}
    tabelas, el = [], d.achar("Sócios:")
    while el is not None and el.getparent() is not d.body:
        el = el.getparent()
    while el is not None and len(tabelas) < 2:
        el = el.getnext()
        if el is not None and el.tag == W + "tbl":
            tabelas.append([tr.findall(W + "tc") for tr in el.iter(W + "tr")])
    for linhas, mes in zip(tabelas, ("jan", "fev")):
        for chave, trecho in func.items():
            cels = _linha(linhas, chave)
            s = next((s for s in v["socios"] if trecho in (s["funcao"] or "").lower()), None)
            if cels and s and len(cels) > 1:
                definir(cels[1], f"R$ {brl(s.get(f'pro_labore_{mes}') or 0)}")


def _folha(d: Doc, v: dict) -> None:
    for ancora, mes in (("Dados para elaboração da folha de pagamento janeiro", "jan"),
                        ("Dados para elaboração da folha de pagamento fevereiro", "fev")):
        linhas = d.tabela_apos(ancora)
        for f in v["folha"]:
            cels = _linha(linhas, f["nome"])
            if not cels or len(cels) < 4:
                continue
            sal, he, com = f.get(f"salario_{mes}"), f.get(f"he_{mes}"), f.get(f"comissao_{mes}")
            if sal is not None:
                definir(cels[3], brl(sal))
            if len(cels) > 4 and _txt(cels[4]).strip() not in ("", "-"):
                definir(cels[4], brl(he) if he else "-")
            if len(cels) > 5 and _txt(cels[5]).strip() not in ("", "-"):
                definir(cels[5], brl(com) if com else "-")


def _contratos(d: Doc, x: Valores) -> None:
    lim = x.p("contrato", "C01", "limite")
    if lim is not None:
        d.trocar("uma conta garantida", re.compile(r"R\$ [\d.]+,\d\d \([^)]*\)"), f"R$ {brl(lim)} ({extenso(lim)} reais)", 1)
    tj = x.p("contrato", "C01", "taxa")
    if tj is not None:
        d.trocar("uma conta garantida", re.compile(r"de [\d,]+% ao mês"), f"de {pct(tj)}% ao mês", 1)
    tr = x.p("contrato", "C02", "taxa")
    if tr is not None:
        d.trocar("INVEST LIQUID”, com resgate", re.compile(r"taxa de [\d,]+% ao mês"), f"taxa de {pct(tr)}% ao mês", 1)
        d.trocar("Realizada aplicação Financeira", re.compile(r"taxa de [\d,]+% a\.m\."), f"taxa de {pct(tr)}% a.m.", 1)
    vm, tl, pz = x.p("contrato", "C04", "valor"), x.p("contrato", "C04", "taxa"), x.p("contrato", "C04", "prazo")
    if vm is not None:
        d.trocar("Contrato de Leasing Financeiro", re.compile(r"máquinas é de R\$ [\d.]+,\d\d"), f"máquinas é de R$ {brl(vm)}")
    if tl is not None:
        d.trocar("Contrato de Leasing Financeiro", re.compile(r"compostos de [\d,]+% ao ano"), f"compostos de {fmt(float(tl), 1)}% ao ano")
    if pz is not None:
        d.trocar("Contrato de Leasing Financeiro", re.compile(r"prazo de pagamento de \d+ meses"), f"prazo de pagamento de {int(pz)} meses")
    h = x.p("contrato", "C05", "honor")
    if h is not None:
        d.trocar("prestação de serviços de seleção", re.compile(r"valor bruto de R\$ [\d.]+,\d\d"), f"valor bruto de R$ {brl(h)}")
    hc, rj = x.p("contrato", "C06", "honorário"), x.p("contrato", "C06", "reajuste")
    if hc is not None:
        d.trocar("assessoria contábil. O escritório", re.compile(r"mensal de R\$ [\d.]+,\d\d"), f"mensal de R$ {brl(hc)}")
        if rj is not None:
            novo = round(hc * (1 + rj / 100) / 100) * 100
            d.trocar("assessoria contábil. O escritório", re.compile(r"reajustados para R\$ [\d.]+,\d\d"), f"reajustados para R$ {brl(novo)}")
    mi = x.p("contrato", "C07", "mensalidade")
    if mi is not None:
        d.trocar("cable modem", re.compile(r"R\$ [\d.]+,\d\d por mês"), f"R$ {brl(mi)} por mês")
    mc, qa = x.p("contrato", "C08", "mensalidade"), x.p("contrato", "C08", "quantidade")
    if mc is not None:
        d.trocar("aparelhos celulares", re.compile(r"R\$ [\d.]+,\d\d por mês"), f"R$ {brl(mc)} por mês")
    if qa is not None:
        d.trocar("aparelhos celulares", re.compile(r"de \d+ aparelhos"), f"de {int(qa)} aparelhos")
    mu = x.p("contrato", "C10", "valor")
    tm = x.p("contrato", "C10", "taxa")
    if mu is not None:
        d.trocar("com a sócia Cassilda Apedeuta, no valor", re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(mu)}")
        d.trocar("Cessão de mútuo financeiro", re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(mu)}")
    if tm is not None:
        d.trocar("com a sócia Cassilda Apedeuta, no valor", re.compile(r"composta de [\d,]+% ao mês"), f"composta de {fmt(float(tm), 1)}% ao mês")
    va = x.p("contrato", "C11", "valor")
    if va is not None:
        d.trocar("arquiteto profissional autônomo", re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(va)}")
    vr, pm = x.p("contrato", "C12", "valor"), x.p("contrato", "C12", "material")
    if vr is not None:
        d.trocar("reforma de galpão industrial", re.compile(r"contrato de reforma é de R\$ [\d.]+,\d\d"), f"contrato de reforma é de R$ {brl(vr)}")
    if pm is not None:
        d.trocar("reforma de galpão industrial", re.compile(r"\(sendo: \d+% correspondente ao material aplicado e \d+% aos"),
                 f"(sendo: {int(pm)}% correspondente ao material aplicado e {100 - int(pm)}% aos")
    ca, tc = x.p("contrato", "C03", "valor"), x.p("contrato", "C03", "taxa")
    if ca is not None:
        d.trocar("“CDB Renda Mais”, à taxa", re.compile(r"Retirada de R\$ [\d.]+,\d\d"), f"Retirada de R$ {brl(ca)}")
    if tc is not None:
        d.trocar("“CDB Renda Mais”, à taxa", re.compile(r"taxa de [\d,]+% a\.m\."), f"taxa de {pct(tc)}% a.m.")


def _conta_consumo(d, linhas, rotulo, valor, tarifa, casas, sufixo=""):
    cels = _linha(linhas, rotulo)
    if not cels or len(cels) < 4:
        return
    q = valor / tarifa
    definir(cels[1], f"{fmt(q, casas)}{sufixo}")
    atual = _txt(cels[3])
    definir(cels[3], f"R$ {brl(valor)}" if atual.strip().startswith("R$") else brl(valor))


def _eventos(d: Doc, x: Valores) -> None:
    # J02 - energia de janeiro
    tot, adm = x.p("evento", "J02", "valor total"), x.p("evento", "J02", "administrativa")
    if tot is not None:
        tarifa = x.p("evento", "J02", "tarifa", 1.4316)
        v_adm = round(tot * (adm or 46.4) / 100 / 10) * 10
        linhas = d.tabela_apos("sob o n.º 987321")
        _conta_consumo(d, linhas, "Área Administrativa", v_adm, tarifa, 3)
        _conta_consumo(d, linhas, "Área Comercial", tot - v_adm, tarifa, 3)
        cels = _linha(linhas, "Totais")
        if cels:
            definir(cels[1], fmt(tot / tarifa, 3).replace(".", ""))
            definir(cels[-1], brl(tot))
        d.trocar("sob o n.º 987321", re.compile(r"consumo de [\d.,]+ kWh"), f"consumo de {fmt(tot / tarifa, 3)} kWh")
        d.trocar("sob o n.º 987321", re.compile(r"total a pagar de R\$ [\d.]+,\d\d"), f"total a pagar de R$ {brl(tot)}")
    # J03 - água de janeiro (administrativa 210 e comercial 380 no exercício-base)
    tot = x.p("evento", "J03", "valor total")
    if tot is not None:
        tarifa = x.p("evento", "J03", "tarifa", 23.62)
        v_adm = round(tot * 210 / 590 / 10) * 10
        linhas = d.tabela_apos("sob o n.º 321654")
        _conta_consumo(d, linhas, "Área Administrativa", v_adm, tarifa, 3)
        _conta_consumo(d, linhas, "Área Comercial", tot - v_adm, tarifa, 3)
        cels = _linha(linhas, "Totais")
        if cels:
            definir(cels[1], fmt(tot / tarifa, 3))
            definir(cels[-1], brl(tot))
        d.trocar("sob o n.º 321654", re.compile(r"consumo de [\d.,]+ m³"), f"consumo de {fmt(tot / tarifa, 3)} m³")
        d.trocar("sob o n.º 321654", re.compile(r"total de R\$ [\d.]+,\d\d"), f"total de R$ {brl(tot)}")
    ap = x.p("evento", "J04", "valor")
    if ap is not None:
        d.trocar("Realizada aplicação Financeira", re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(ap)}")
    # J05/F03 - telefonia (fixo sorteado no evento; celular e internet pelos contratos C08 e C07)
    for ref, ancora in (("J05", "telefonia e internet utilizados no mês de janeiro"), ("F03", "telefonia e internet utilizados no mês de fevereiro")):
        linhas = d.tabela_apos(ancora)
        fx = x.p("evento", ref, "telefone")
        for rot, val in (("Telefone Fixo", fx), ("Celular", x.p("contrato", "C08", "mensalidade")),
                         ("Internet", x.p("contrato", "C07", "mensalidade"))):
            cels = _linha(linhas, rot)
            if cels and val is not None:
                definir(cels[-1], brl(val))
    # J08/J09 - ar-condicionados e frete
    q, vu, ent = x.p("evento", "J08", "quantidade"), x.p("evento", "J08", "unitário"), x.p("evento", "J08", "entrada")
    if q is not None and vu is not None:
        d.trocar("Ar Frio Ltda., do Estado", re.compile(r"compra de \d+ ar-condicionados"), f"compra de {int(q):02d} ar-condicionados")
        d.trocar("Ar Frio Ltda., do Estado", re.compile(r"valor total de R\$ [\d.]+,\d\d"), f"valor total de R$ {brl(q * vu)}")
    if ent is not None:
        d.trocar("Ar Frio Ltda., do Estado", re.compile(r"sendo \d+% à vista"), f"sendo {int(ent)}% à vista")
    fr = x.p("evento", "J09", "frete")
    if fr is not None:
        d.trocar("Conhecimento n° 322.123", re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(fr)}")
    # J15 - ALPHA (Comercial Elegante)
    q, cu = x.p("evento", "J15", "quantidade"), x.p("evento", "J15", "custo")
    an = "Nota Fiscal n.º 3.369, emitida por Comercial Elegante"
    if q is not None and cu is not None:
        d.trocar(an, re.compile(r"compra de [\d.]+ unidades"), f"compra de {inteiro(q)} unidades")
        d.trocar(an, re.compile(r"no valor total de R\$ [\d.]+,\d\d, sendo"), f"no valor total de R$ {brl(q * cu)}, sendo")
    ds = x.p("evento", "J15", "desconto")
    if ds is not None:
        d.trocar(an, re.compile(r"desconto incondicional de [\d,]+%"), f"desconto incondicional de {pct(ds)}%")
    fr = x.p("evento", "J15", "frete")
    if fr is not None:
        d.trocar(an, re.compile(r"Frete Confiança Ltda\., no valor total de R\$ [\d.]+,\d\d"), f"Frete Confiança Ltda., no valor total de R$ {brl(fr)}")
    for ref, an in (("J16", "Nota Fiscal de Serviço n.º 002"), ("F08", "Nota Fiscal de Serviço n.º 003, emitida para Algodão")):
        c = x.p("evento", ref, "comissão")
        if c is not None:
            d.trocar(an, re.compile(r"valor de R\$ [\d.]+,\d\d"), f"valor de R$ {brl(c)}")
    for ref, an in (("J27", "Saída de Nota Fiscal n.º 001"), ("F26", "Nota Fiscal n.º 003, emitida para Comercial Caribe")):
        q = x.p("evento", ref, "quantidade")
        if q is not None:
            d.trocar(an, re.compile(r"revenda de [\d.]+ unidades"), f"revenda de {inteiro(q)} unidades")
    # J29 - auto de infração
    b = x.p("evento", "J29", "base")
    if b is not None:
        aliq = x.p("evento", "J29", "alíquota", 18.0)
        icms = round(b * aliq / 100, 2)
        multa = round(icms * 0.75, 2)
        d.trocar("adquiriu mercadorias sem documentos", re.compile(r"valor total de R\$ [\d.]+,\d\d"), f"valor total de R$ {brl(b)}")
        p = d.achar("Base de cálculo: R$")
        if p is not None:
            trocar(p, re.compile(r"Base de cálculo: R\$ [\d.]+,\d\d"), f"Base de cálculo: R$ {brl(b)}")
            trocar(p, re.compile(r"(ICMS:\s*R\$ )[\d.]+,\d\d"), lambda m: f"{m.group(1)}{brl(icms)}")
        d.trocar("Multa:", re.compile(r"R\$ [\d.,]+"), f"R$ {brl(multa)}", depois=p)
        d.trocar("Total:", re.compile(r"R\$ [\d.,]+"), f"R$ {brl(icms + multa)}", depois=p)
    # compras de insumos (quantidade = necessidade + sobra; custo do insumo)
    for cod, an in (("MP-A", "Nota Fiscal n.º 23.456, emitida por Indústria Sofisticada"),
                    ("MP-B", "Nota Fiscal n.º 12.380, emitida por Indústria Zalego"),
                    ("ME-H", "Nota Fiscal n.º 1.747, emitida por Embalagens")):
        i = x.insumo(cod)
        if not i:
            continue
        d.trocar(an, re.compile(r"compra de [\d.]+,? unidades"), f"compra de {inteiro(i['compra'])} unidades")
        d.trocar(an, re.compile(r"no valor total de R\$ [\d.]+,\d\d, sendo"), f"no valor total de R$ {brl(i['valor_compra'])}, sendo")
    for ref, an, depois in (("J30", "Nota Fiscal n.º 23.456, emitida por Indústria Sofisticada", None),
                            ("F22", "Nota Fiscal n.º 1.747, emitida por Embalagens", None)):
        fr = x.p("evento", ref, "frete")
        if fr is not None:
            d.trocar(an, re.compile(r"Frete Confiança Ltda\., no valor total de R\$ [\d.]+,\d\d"), f"Frete Confiança Ltda., no valor total de R$ {brl(fr)}")
    ds = x.p("evento", "F05", "desconto")
    if ds is not None:
        d.trocar("Nota Fiscal n.º 12.380, emitida por Indústria Zalego", re.compile(r"\(condicional\) de [\d,]+%"), f"(condicional) de {pct(ds)}%")
    fr = x.p("evento", "F05", "frete")
    if fr is not None:
        d.trocar("Transportes Rodoviário e de Cargas n.º 424.110, da Nota Fiscal n.º 12.380, emitido por Frete Confiança Ltda., no valor",
                 re.compile(r"valor total de R\$ [\d.]+,\d\d"), f"valor total de R$ {brl(fr)}")
    # F10 - materiais secundários (tabela)
    linhas = d.tabela_apos("Nota Fiscal n.º 9.147")
    total = 0.0
    for cod in ("MS-Z", "MS-Q", "MS-R", "MS-K"):
        i = x.insumo(cod)
        cels = _linha(linhas, cod)
        if i and cels and len(cels) >= 3:
            definir(cels[1], inteiro(i["compra"]))
            definir(cels[2], brl(i["valor_compra"]))
            total += i["valor_compra"]
    cels = _linha(linhas, "Totais")
    if cels and total:
        definir(cels[-1], brl(total))
        d.trocar("Nota Fiscal n.º 9.147", re.compile(r"valor total de R\$ [\d.]+,\d\d"), f"valor total de R$ {brl(total)}")
    # F01/F02 - energia e água de fevereiro (rateio proporcional ao exercício-base)
    tot = x.p("evento", "F01", "valor total")
    if tot is not None:
        tarifa = x.p("evento", "F01", "tarifa", 1.432)
        t_calc = tarifa * 1.4316 / 1.432  # o exercício mostra 1,432 mas calcula o consumo com 1,4316
        base = x.base("evento", "F01", "valor total") or 3400
        linhas = d.tabela_apos("sob o n.º 988.333")
        partes = {rot: round(vb * tot / base / 10) * 10 for rot, vb in (("Área Comercial", 590), ("Produto X", 1070), ("Produto Y", 1210))}
        partes["Área Administrativa"] = round(tot - sum(partes.values()), 2)  # 530 no exercício-base
        partes["Totais"] = tot
        for rot, val in partes.items():
            cels = _linha(linhas, rot)
            if cels:
                definir(cels[1], f"{fmt(val / t_calc, 3)} kWh")
                definir(cels[3], f"R$ {brl(val)}")
        d.trocar("sob o n.º 988.333", re.compile(r"consumo de [\d.,]+ kWh"), f"consumo de {fmt(tot / t_calc, 3)} kWh")
        d.trocar("sob o n.º 988.333", re.compile(r"total a pagar de R\$ [\d.]+,\d\d"), f"total a pagar de R$ {brl(tot)}")
    tot = x.p("evento", "F02", "valor total")
    if tot is not None:
        tarifa = x.p("evento", "F02", "tarifa", 23.62)
        base = x.base("evento", "F02", "valor total") or 1780
        linhas = d.tabela_apos("sob o n.º 322.666")
        partes = {rot: round(vb * tot / base / 10) * 10 for rot, vb in (("Área Administrativa", 280), ("Área Comercial", 320), ("Produto X", 610))}
        partes["Produto Y"] = round(tot - sum(partes.values()), 2)  # 570 no exercício-base
        partes["Totais"] = tot
        for rot, val in partes.items():
            cels = _linha(linhas, rot)
            if cels:
                definir(cels[1], f"{fmt(val / tarifa, 4)} m³")
                definir(cels[3], f"R$ {brl(val)}")
        d.trocar("sob o n.º 322.666", re.compile(r"consumo de [\d.,]+ m³"), f"consumo de {fmt(tot / tarifa, 4)} m³")
        d.trocar("sob o n.º 322.666", re.compile(r"total a pagar de R\$ [\d.]+,\d\d"), f"total a pagar de R$ {brl(tot)}")
    q = x.p("evento", "F04", "quantidade")
    if q is not None:
        d.trocar("Emissão de nota fiscal n.º 337", re.compile(r"venda de \d+ unidades"), f"venda de {int(q)} unidades")
    q = x.p("evento", "F28", "devolvida")
    if q is not None:
        d.trocar("Devolução de", re.compile(r"Devolução de [\d.]+ unidades"), f"Devolução de {inteiro(q)} unidades")
    q = x.p("evento", "F36", "devolvida")
    if q is not None:
        d.trocar("Nota Fiscal n.º 1.320", re.compile(r"devolução de \d+ unidades"), f"devolução de {int(q)} unidades")
    # F34 - venda dos produtos X e Y
    rc = x.p("evento", "F34", "recebimento")
    if rc is not None:
        d.trocar("Nota Fiscal n.º 005, emitida para Comercial Roma", re.compile(r"de \d+% na emissão"), f"de {int(rc)}% na emissão")
    for cod in ("X", "Y"):
        pr = x.produto(cod)
        if pr:
            d.trocar(f"Produto {cod} (NCM –", re.compile(r"[\d.]+ unidades"), f"{inteiro(pr['vendido'])} unidades", 1)
    ds = x.p("evento", "F34", "desconto")
    if ds is not None:
        d.trocar("desconto financeiro de", re.compile(r"de [\d,]+% sobre a venda"), f"de {brl(ds)}% sobre a venda")


def _balanco(d: Doc, v: dict) -> None:
    """Capital social no PL e Banco Rico como conta de fechamento (Ativo = Passivo + PL)."""
    linhas = []
    for el in d.body.iter(W + "tbl"):
        for tr in el.iter(W + "tr"):
            tcs = tr.findall(W + "tc")
            if len(tcs) == 3:
                cod = _txt(tcs[0]).strip()
                m = re.fullmatch(r"([\d.,]+) ([DC])", _txt(tcs[2]).strip())
                if re.fullmatch(r"[12](\.[\d-]+)*", cod) and m:
                    linhas.append({"cod": cod, "nome": _txt(tcs[1]), "cel": tcs[2],
                                   "v": num(m.group(1)) * (1 if m.group(2) == ("D" if cod.startswith("1") else "C") else -1)})
    if not linhas:
        return
    por_cod = {l["cod"]: l for l in linhas}

    def ajustar(cod: str, delta: float):
        alvo = por_cod.get(cod)
        if alvo is None or abs(delta) < 0.005:
            return
        for l in linhas:
            if l["cod"] == cod or cod.startswith(l["cod"] + "."):
                l["v"] = round(l["v"] + delta, 2)
                l["mudou"] = True

    delta_pl = 0.0
    for s in v.get("socios", []):
        for l in linhas:
            if l["cod"].startswith("2.07.01.01.01.") and normalizar(s["nome"]) in normalizar(l["nome"]):
                d_cap = float(s["cotas"] or 0) - l["v"]
                ajustar(l["cod"], d_cap)
                delta_pl += d_cap
            if l["cod"].startswith("2.07.01.01.03.") and normalizar(s["nome"]) in normalizar(l["nome"]):
                d_int = -float(s["a_integralizar"] or 0) - l["v"]
                ajustar(l["cod"], d_int)
                delta_pl += d_int
    banco = next((l for l in linhas if "BANCO RICO" in normalizar(l["nome"]) and l["cod"].startswith("1.")), None)
    if banco and abs(delta_pl) >= 0.005:
        ajustar(banco["cod"], delta_pl)
        # o 2.07.01.01.03 é conta redutora: o pai soma os filhos com sinal
    for l in linhas:
        if l.get("mudou"):
            lado = ("D" if l["v"] >= 0 else "C") if l["cod"].startswith("1") else ("C" if l["v"] >= 0 else "D")
            definir(l["cel"], f"{brl(abs(l['v']))} {lado}")
    # mesmo valor no parágrafo de abertura? (não há); tabela "Capital Social" do PL já ajustada


# ------------------------------------------------------------------ geração
def gerar_docx(valores: dict, rotulo: str) -> tuple[bytes, list[str]]:
    d = Doc(MODELO)
    x = Valores(valores)
    _capa(d, valores, rotulo)
    _capital(d, valores)
    _balanco(d, valores)
    _destinacao(d, x)
    _producao(d, x)
    _socios_prolabore(d, valores)
    _folha(d, valores)
    _contratos(d, x)
    _eventos(d, x)
    buf = io.BytesIO()
    d.doc.core_properties.title = f"{valores['empresa'].get('nome', 'Empresa LAB')} · {rotulo}"
    d.doc.save(buf)
    return buf.getvalue(), d.avisos
