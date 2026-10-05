"""Central de documentos (Etapa 4): documentos-fonte de cada evento de janeiro, com os valores da dupla.

Os documentos trazem só os dados de origem (quantidades, preços, impostos destacados, vencimentos) —
nunca a contabilização. Quando o próprio exercício pede que a dupla calcule um valor (preço pelo mark-up,
retenções do RPA e da reforma), o campo aparece como "a calcular pela dupla".
Todos os documentos são didáticos: emitentes e CNPJs fictícios e a marca "sem valor fiscal".
"""
from __future__ import annotations

import hashlib

from .gabarito import ALIQ_IPI, ICMS_INTERESTADUAL, ISS_FORTALEZA, IRRF_SERVICOS, CSRF, ICMS_INTERNO_CE, r2
from .caso_servico import fmt
from .orientacao import Valores


def cnpj_ficticio(nome: str) -> str:
    """CNPJ com dígitos verificadores válidos, derivado do nome (sempre o mesmo para o mesmo emitente)."""
    h = int(hashlib.sha1(nome.encode()).hexdigest(), 16)
    base = [int(c) for c in f"{h % 10**8:08d}"] + [0, 0, 0, 1]

    def dv(nums, pesos):
        s = sum(n * p for n, p in zip(nums, pesos)) % 11
        return 0 if s < 2 else 11 - s
    d1 = dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = dv(base + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    n = "".join(map(str, base + [d1, d2]))
    return f"{n[:2]}.{n[2:5]}.{n[5:8]}/{n[8:12]}-{n[12:]}"


def _parte(nome: str, uf: str = "CE", cidade: str = "", ie: bool = True) -> dict:
    return {"nome": nome, "uf": uf, "cidade": cidade, "cnpj": cnpj_ficticio(nome)}


def gerar_documentos(valores: dict) -> list[dict]:
    x = Valores(valores)

    def p(escopo, ref, trecho, padrao=None):
        v = x.p(escopo, ref, trecho)
        return padrao if v is None else float(v)

    emp = valores.get("empresa", {}) or {}
    empresa = _parte(emp.get("nome") or "Empresa LAB", "CE", "Fortaleza")
    docs: list[dict] = []

    def add(**d):
        d["id"] = f"{d['evento']}-{sum(1 for x in docs if x['evento'] == d['evento']) + 1}"
        docs.append(d)

    # J02 energia
    tot = p("evento", "J02", "valor total")
    if tot:
        tarifa = p("evento", "J02", "tarifa", 1.4316)
        add(evento="J02", data="2026-01-02", tipo="fatura", titulo="Conta de energia elétrica (modelo 6)", numero="987321",
            emitente=_parte("Luz do Sertão Energia S.A. (fictícia)", "CE", "Fortaleza"), destinatario=empresa,
            classe="B3 - Demais classes (comercial, industrial e poder público)", referencia="01/2026", vencimento="2026-01-14",
            itens=[{"descricao": "Consumo de energia ativa", "quantidade": round(tot / tarifa, 3), "unidade": "kWh",
                    "unitario": tarifa, "total": tot}], total=tot,
            obs="A distribuição do valor entre as áreas da empresa está na orientação da dupla.")
    # J03 água
    tot = p("evento", "J03", "valor total")
    if tot:
        tarifa = p("evento", "J03", "tarifa", 23.62)
        add(evento="J03", data="2026-01-05", tipo="fatura", titulo="Fatura de água e esgoto", numero="321654",
            emitente=_parte("Águas do Litoral Saneamento S.A. (fictícia)", "CE", "Fortaleza"), destinatario=empresa,
            classe="Industrial - demanda mínima de 15 m³ de água e 12 m³ de esgoto", referencia="01/2026", vencimento="2026-01-14",
            itens=[{"descricao": "Água e esgoto", "quantidade": round(tot / tarifa, 3), "unidade": "m³", "unitario": tarifa,
                    "total": tot}], total=tot)
    # J05 telefonia e internet
    for desc, emit, val, venc in (("Telefone fixo", "Operadora de Telefonia Fixa", p("evento", "J05", "telefone"), "2026-02-24"),
                                  ("Celulares em comodato", "Cell Telefonia Ltda.", p("contrato", "C08", "mensalidade", 480), "2026-02-08"),
                                  ("Internet (cable modem em comodato)", "Internet & Comunicação Ltda.", p("contrato", "C07", "mensalidade", 350), "2026-02-10")):
        if val:
            add(evento="J05", data="2026-01-06", tipo="fatura", titulo=f"Nota fiscal de serviço de comunicação - {desc.lower()}",
                numero="", emitente=_parte(emit, "CE", "Fortaleza"), destinatario=empresa, referencia="01/2026", vencimento=venc,
                itens=[{"descricao": desc, "quantidade": 1, "unidade": "mês", "unitario": val, "total": val}], total=val)
    # J08 NF-e ar-condicionados
    q, vu, ent = p("evento", "J08", "quantidade"), p("evento", "J08", "unitário"), p("evento", "J08", "entrada", 20)
    if q and vu:
        valor = r2(q * vu)
        vista = r2(valor * ent / 100)
        parc = r2((valor - vista) / 2)
        add(evento="J08", data="2026-01-08", tipo="nfe", titulo="NF-e - venda de mercadoria adquirida de terceiros", numero="7.852",
            emitente=_parte("Ar Frio Ltda.", "MA"), destinatario=empresa, natureza="Venda de mercadoria", cfop="6.102",
            itens=[{"codigo": "AC-01", "descricao": "Aparelho de ar-condicionado", "ncm": "8415.10.11", "cfop": "6.102", "unidade": "un",
                    "quantidade": q, "unitario": vu, "total": valor, "aliq_icms": 12.0, "aliq_ipi": 0.0}],
            produtos=valor, desconto=0, frete=0, base_icms=valor, icms=r2(valor * ICMS_INTERESTADUAL["MA"]), ipi=0, total=valor,
            duplicatas=[("à vista", "2026-01-08", vista), ("001", "2026-02-07", parc), ("002", "2026-03-07", r2(valor - vista - parc))],
            transporte="Por conta do destinatário (CT-e 322.123 - Rodovia Transportes Ltda.)",
            obs="Destinação informada pelo comprador: uso na área administrativa.")
    fr = p("evento", "J09", "frete")
    if fr:
        add(evento="J09", data="2026-01-08", tipo="cte", titulo="CT-e - prestação de serviço de transporte", numero="322.123",
            emitente=_parte("Rodovia Transportes Ltda.", "MA"), destinatario=empresa, cfop="6.353", origem="MA", destino="Fortaleza/CE",
            remetente="Ar Frio Ltda.", nf_ref="7.852", valor=fr, base_icms=fr, aliq_icms=12.0, icms=r2(fr * 0.12),
            pagamento="à vista", tomador="Destinatário")
    # J15 NF-e ALPHA + CT-e
    q, cu, dp = p("evento", "J15", "quantidade"), p("evento", "J15", "custo"), p("evento", "J15", "desconto", 5)
    if q and cu:
        bruto = r2(q * cu)
        desc = r2(bruto * dp / 100)
        liq = r2(bruto - desc)
        vista = r2(liq * 0.20)
        add(evento="J15", data="2026-01-12", tipo="nfe", titulo="NF-e - venda de mercadoria adquirida de terceiros", numero="3.369",
            emitente=_parte("Comercial Elegante Ltda.", "PB"), destinatario=empresa, natureza="Venda de mercadoria", cfop="6.102",
            itens=[{"codigo": "ALPHA", "descricao": "Mercadoria ALPHA (controlador de temperatura)", "ncm": "9032.10.10", "cfop": "6.102",
                    "unidade": "un", "quantidade": q, "unitario": cu, "total": bruto, "aliq_icms": 12.0, "aliq_ipi": 0.0}],
            produtos=bruto, desconto=desc, frete=0, base_icms=liq, icms=r2(liq * ICMS_INTERESTADUAL["PB"]), ipi=0, total=liq,
            duplicatas=[("à vista (20%)", "2026-01-12", vista), ("001", "2026-02-14", r2(liq - vista))],
            transporte="FOB - por conta do destinatário (CT-e 423.765 - Frete Confiança Ltda.)",
            obs=f"Desconto incondicional de {dp:.1f}%".replace(".", ",") + " concedido por pequenas avarias no lote.")
        ff = p("evento", "J15", "frete")
        if ff:
            add(evento="J15", data="2026-01-12", tipo="cte", titulo="CT-e - prestação de serviço de transporte", numero="423.765",
                emitente=_parte("Frete Confiança Ltda.", "PB"), destinatario=empresa, cfop="6.353", origem="PB", destino="Fortaleza/CE",
                remetente="Comercial Elegante Ltda.", nf_ref="3.369", valor=ff, base_icms=ff, aliq_icms=12.0, icms=r2(ff * 0.12),
                pagamento="vencimento em 18/01/2026", tomador="Destinatário (frete FOB)")
    # J16 NFS-e emitida pela empresa
    v = p("evento", "J16", "comissão")
    if v:
        add(evento="J16", data="2026-01-13", tipo="nfse", titulo="NFS-e - representação comercial", numero="002", emitida_pela_empresa=True,
            emitente=empresa, destinatario=_parte("Algodão Doce Ltda.", "CE", "Fortaleza"),
            servico="Comissão pela representação comercial da mercadoria Beta", codigo_servico="10.09 - Representação de qualquer natureza",
            valor=v, aliq_iss=ISS_FORTALEZA * 100, iss=r2(v * ISS_FORTALEZA), iss_retido=False,
            retencoes=[("IRRF (1,5%)", r2(v * IRRF_SERVICOS))], liquido=r2(v - v * IRRF_SERVICOS), vencimento="2026-01-20")
    # J23 RPA
    v = p("contrato", "C11", "valor")
    if v:
        add(evento="J23", data="2026-01-20", tipo="rpa", titulo="Recibo de Pagamento a Autônomo (RPA)", numero="",
            emitente=_parte("Arquiteto autônomo (contribuinte individual)", "CE", "Fortaleza"), destinatario=empresa,
            servico="Projeto de arquitetura para a reforma do galpão industrial", valor=v, vencimento="2026-02-17",
            obs="O profissional tem cadastro ativo na SEFIN de Fortaleza, mas não recolhe ISS por valor fixo. "
                "INSS, IRRF e ISS a reter são calculados pela empresa (campos a preencher pela dupla).")
    # J24 contrato de leasing
    vm = p("contrato", "C04", "valor")
    if vm:
        add(evento="J24", data="2026-01-20", tipo="contrato", titulo="Contrato de arrendamento mercantil financeiro (resumo)",
            numero="C04", emitente=_parte("Banco Rico S/A", "CE", "Fortaleza"), destinatario=empresa,
            clausulas=[("Objeto", "Duas máquinas industriais para o parque fabril, com opção de compra ao final"),
                       ("Valor financiado", f"R$ {vm:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                       ("Taxa de juros", f"{p('contrato', 'C04', 'taxa', 10):.1f}% ao ano, juros compostos, ano civil".replace(".", ",")),
                       ("Prazo", f"{int(p('contrato', 'C04', 'prazo', 18))} parcelas mensais - sistema SAC"),
                       ("Assinatura e liberação", "19/01/2026 (liberação ao fornecedor em 20/01/2026)"),
                       ("1º vencimento", "23/02/2026")])
    # J26 NFS-e reforma
    tot, pm = p("contrato", "C12", "valor"), p("contrato", "C12", "material", 40)
    if tot:
        parc = r2(tot * 0.5)
        add(evento="J26", data="2026-01-22", tipo="nfse", titulo="NFS-e - construção civil (empreitada com material)", numero="6.300",
            emitente=_parte("Construtor Express Ltda.", "CE", "Fortaleza"), destinatario=empresa,
            servico="Reforma do galpão industrial - parcela inicial de 50% do contrato", codigo_servico="7.02 - Execução de obras de construção civil",
            valor=parc, materiais=r2(parc * pm / 100), mao_de_obra=r2(parc * (1 - pm / 100)), aliq_iss=ISS_FORTALEZA * 100,
            iss=None, iss_retido=True, retencoes=[("INSS (retenção pelo tomador)", None), ("ISS (retenção pelo tomador)", None)],
            liquido=None, vencimento="2026-01-22",
            obs=f"Contrato total de R$ {tot:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") +
                "; 2ª e última parcela em 22/02/2026. Retenções a calcular pelo tomador sobre a mão de obra.")
    # J27 NF-e de venda (a emitir pela dupla)
    q = p("evento", "J27", "quantidade")
    if q:
        add(evento="J27", data="2026-01-23", tipo="nfe", titulo="NF-e - venda de mercadoria (a emitir pela dupla)", numero="001",
            emitida_pela_empresa=True, emitente=empresa, destinatario=_parte("Comercial Caribe Ltda.", "CE", "Fortaleza"),
            natureza="Venda de mercadoria adquirida de terceiros", cfop="5.102",
            itens=[{"codigo": "ALPHA", "descricao": "Mercadoria ALPHA (controlador de temperatura)", "ncm": "9032.10.10", "cfop": "5.102",
                    "unidade": "un", "quantidade": q, "unitario": None, "total": None, "aliq_icms": ICMS_INTERNO_CE * 100, "aliq_ipi": 0.0}],
            produtos=None, desconto=0, frete=0, base_icms=None, icms=None, ipi=0, total=None,
            duplicatas=[("boleto Banco Rico", "2026-01-25", None)], transporte="Sem frete",
            obs="Preço unitário calculado pela dupla com base no mark-up (custo médio ponderado móvel).")
    # J29 auto de infração
    b = p("evento", "J29", "base")
    if b:
        aliq = p("evento", "J29", "alíquota", 18)
        icms = r2(b * aliq / 100)
        multa = r2(icms * 0.75)
        add(evento="J29", data="2026-01-26", tipo="auto", titulo="Auto de infração - ICMS", numero="Termo de início 20230001/00",
            emitente=_parte("Secretaria da Fazenda do Estado do Ceará (fiscalização)", "CE", "Fortaleza"), destinatario=empresa,
            infracao="Aquisição de mercadorias sem documento fiscal, apurada em levantamento de estoque",
            base=b, aliq=aliq, icms=icms, multa=multa, reducao="70% da multa para pagamento até 05/02/2026",
            total=r2(icms + multa))
    # J30 NF-e MP-A (indústria)
    ins = x.insumo("MP-A")
    q = float(ins.get("compra") or 0) or p("evento", "J30", "quantidade")
    cu = float(ins.get("custo_unit") or 0) or p("evento", "J30", "custo")
    if q and cu:
        prod = r2(q * cu)
        ipi = r2(prod * ALIQ_IPI["9002.11.11"])
        total = r2(prod + ipi)
        d1, d2 = r2(total * 0.25), r2(total * 0.30)
        add(evento="J30", data="2026-01-26", tipo="nfe", titulo="NF-e - venda de produção do estabelecimento", numero="23.456",
            emitente=_parte("Indústria Sofisticada Ltda.", "MG"), destinatario=empresa, natureza="Venda de produção do estabelecimento", cfop="6.101",
            itens=[{"codigo": "MP-A", "descricao": "Matéria-prima A - elemento óptico", "ncm": "9002.11.11", "cfop": "6.101", "unidade": "un",
                    "quantidade": q, "unitario": cu, "total": prod, "aliq_icms": 7.0, "aliq_ipi": ALIQ_IPI["9002.11.11"] * 100}],
            produtos=prod, desconto=0, frete=0, base_icms=prod, icms=r2(prod * ICMS_INTERESTADUAL["MG"]), ipi=ipi, total=total,
            duplicatas=[("à vista (25%)", "2026-01-26", d1), ("001 (30%)", "2026-02-26", d2), ("002 (45%)", "2026-03-24", r2(total - d1 - d2))],
            transporte=f"CIF - por conta do emitente (CT-e 423.951 - Frete Confiança Ltda., R$ {fmt(p('evento', 'J30', 'frete', 0), 2)})")
    # J39 NFS-e contador
    h = p("contrato", "C06", "honorário", 5500)
    if h:
        add(evento="J39", data="2026-01-30", tipo="nfse", titulo="NFS-e - assessoria contábil", numero="023",
            emitente=_parte("Contador Formado S/S", "CE", "Fortaleza"), destinatario=empresa,
            servico="Serviços de assessoria contábil - competência janeiro/2026", codigo_servico="17.19 - Contabilidade",
            valor=h, aliq_iss=ISS_FORTALEZA * 100, iss=r2(h * ISS_FORTALEZA), iss_retido=False,
            retencoes=[("IRRF (1,5%)", r2(h * IRRF_SERVICOS)), ("CSRF - PIS/COFINS/CSLL (4,65%)", r2(h * CSRF))],
            liquido=r2(h - h * IRRF_SERVICOS - h * CSRF), vencimento="2026-02-10")
    docs.sort(key=lambda d: (d["data"], d["evento"]))
    return docs
