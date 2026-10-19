"""Atualização única dos casos já cadastrados para o exercício revisado pelo professor (PDF de 07/10/2026).

O caso-base (JSON) já vem atualizado para instalações novas. Nos bancos existentes, cada caso recebe as
mesmas correções, sem sobrescrever o que o professor tenha alterado (só troca valores iguais aos antigos):
- dividendos de 60% para 50% (P24);
- seguro em 3 parcelas (C09) e J21 como "3ª e última parcela";
- Renato Português com salário de R$ 2.120,00 em fevereiro;
- saldos de abertura: ICMS a recolher 43.361,80 e depreciação acumulada 10.408,34;
- observações das faturas de água e energia (rateios completos) e a lista de inconsistências.
Em seguida, as empresas das duplas desses casos são recalculadas com a mesma semente.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .caso_servico import CASO_BASE, num
from .fuso import AjusteSistema
from .models_caso import Caso, Inconsistencia

CHAVE = "exercicio_revisado_2026_10_07"
OBS_ANTIGA = "Tabela original"
ONDE_ANTIGO = {"Aplicações (J04, J14, F07, F47)": "Aplicações (J14, F07)"}
RESOLVIDAS = {"Energia e água (J03, F01, F02)", "Imobilizado"}
ATUALIZADAS = {"Seguro (C09, J21)", "Aplicações (J14, F07)", "Folha (funcionários)", "Materiais secundários (F10)"}
NOVA = "Balanço de 31/12/2025 (versão de 07/10)"


def _base_json() -> dict:
    return json.loads(CASO_BASE.read_text(encoding="utf-8"))


def _ajustar_caso(caso: Caso, ref: dict) -> bool:
    mudou = False
    for p in caso.parametros:
        if p.escopo == "empresa" and p.nome.lower().startswith("dividendos"):
            if num(p.base) == 60:
                p.base, mudou = "50", True
            if p.maximo == 60:
                p.maximo, mudou = 50.0, True
        if p.escopo == "contrato" and p.ref == "C09" and p.nome.lower().startswith("número de parcelas") and num(p.base) == 4:
            p.base, p.minimo, p.maximo, p.passo, p.varia, mudou = "3", None, None, None, False, True
    c09 = next((c for c in ref["contratos"] if c["id"] == "C09"), None)
    for c in caso.contratos:
        if c.codigo == "C09" and c09 and (c.descricao or "").startswith("Cobertura de 12 meses; prêmio em parcelas mensais"):
            c.descricao, mudou = c09["descricao"], True
    obs = {e["id"]: e.get("obs") for e in ref["eventos"]}
    for e in caso.eventos:
        if e.codigo == "J21" and "4ª parcela" in (e.descricao or ""):
            e.descricao, mudou = e.descricao.replace("4ª parcela", "3ª e última parcela"), True
        if e.codigo in ("J03", "F01", "F02") and (e.obs or "").startswith(OBS_ANTIGA):
            e.obs, mudou = obs.get(e.codigo), True
    for f in caso.funcionarios:
        if f.nome == "Renato Português" and f.salario_fev is None and f.salario_jan is None:
            f.salario_fev, mudou = 2120.0, True
    # saldos de abertura (dados do caso, JSON)
    dados = dict(caso.dados or {})
    si = json.loads(json.dumps(dados.get("saldos_iniciais") or {}))
    pas, atv = si.get("passivo") or {}, si.get("ativo") or {}
    if pas.get("ICMS a recolher") == 43361.81:
        pas["ICMS a recolher"], mudou = 43361.80, True
    dep = atv.get("(-) Depreciação acumulada") or {}
    if dep.get("valor") == -10408.33:
        dep["valor"], mudou = -10408.34, True
    maq = atv.get("Máquinas e equipamentos industriais") or {}
    if "obs" in maq and "62.000" in maq["obs"]:
        maq.pop("obs")
        mudou = True
    if mudou:
        dados["saldos_iniciais"] = si
        caso.dados = dados
    # inconsistências
    novas = {x["onde"]: x for x in ref["inconsistencias"]}
    existentes = {x.onde: x for x in caso.inconsistencias}
    for antigo, novo in ONDE_ANTIGO.items():
        if antigo in existentes and novo not in existentes:
            existentes[antigo].onde = novo
            existentes[novo] = existentes.pop(antigo)
            mudou = True
    for onde in ATUALIZADAS:
        x = existentes.get(onde)
        if x and x.status == "PENDENTE" and "Corrigido em 07/10" not in (x.descricao or ""):
            x.descricao, mudou = novas[onde]["descricao"], True
    for onde in RESOLVIDAS:
        x = existentes.get(onde)
        if x and x.status == "PENDENTE":
            x.status, x.decisao, mudou = "RESOLVIDA", (x.decisao or novas[onde]["decisao"]), True
    if NOVA not in existentes and caso.inconsistencias:
        caso.inconsistencias.append(Inconsistencia(onde=NOVA, descricao=novas[NOVA]["descricao"], status="PENDENTE"))
        mudou = True
    return mudou


def aplicar(db: Session) -> int:
    """Aplica as correções uma única vez. Retorna quantos casos mudaram."""
    if db.get(AjusteSistema, CHAVE):
        return 0
    from .geracao import gerar
    from .models_dupla import EmpresaGerada

    ref = _base_json()
    alterados = [c for c in db.query(Caso).all() if _ajustar_caso(c, ref)]
    db.flush()
    n_emp = 0
    for caso in alterados:
        for e in db.query(EmpresaGerada).filter_by(caso_id=caso.id).all():
            d = e.dupla
            base = (e.valores or {}).get("modo") == "caso-base"
            valores = gerar(caso, e.semente, d.rotulo, None if base else d.numero, base=base)
            valores["integrantes"] = (e.valores or {}).get("integrantes", [])
            e.valores = valores
            n_emp += 1
    db.add(AjusteSistema(chave=CHAVE, detalhe=f"{len(alterados)} caso(s), {n_emp} empresa(s) recalculada(s)"))
    db.commit()
    return len(alterados)


# ---------------------------------------------------------------------------------------------------------------
# Decisões do professor de 11/10/2026 (coluna "Correção" da conferência das inconsistências)
CHAVE_1110 = "exercicio_correcoes_2026_10_11"
# parâmetros: (ref, início do nome) -> (base antiga, base nova, mínimo, máximo)
PARAMS_1110 = {
    ("C07", "mensalidade"): (350, 410, 300.0, 550.0),
    ("C08", "mensalidade"): (480, 580, 400.0, 750.0),
    ("C10", "valor"): (20000, 30000, 20000.0, 45000.0),
}
# eventos: código -> data antiga (None = só a descrição muda)
EVENTOS_1110 = {
    "J24": "2026-01-20", "F06": "2026-02-04", "F17": "2026-02-12",
    "F11": None, "F27": None, "F41": None,
}
DESCRICOES_ANTIGAS_1110 = {
    "F06": "Pagamento do auto de infração",
    "F11": "Pagamento parcial da NF 7.852 (Ar Frio)",
    "F27": "Cessão de mútuo à sócia Cassilda Apedeuta",
    "F41": "NFS-e 345 Recrutamento S/S - seleção de pessoal (jan-fev)",
}
DEPENDENTES_FEV_ANTIGOS = {
    "Alves Africano": "2 (11 e 15 anos)", "Venâncio Australiano": "1 (7 anos)", "Tiago Espanhol": "1 (8 anos)",
    "Ângela Peruana": "2 (12 e 14 anos)", "Marena Russa": "1 (6 anos)",
}


def _ajustar_caso_1110(caso: Caso, ref: dict) -> bool:
    from datetime import date

    mudou = False
    for p in caso.parametros:
        if p.escopo != "contrato":
            continue
        for (cod, ini), (antigo, novo, mn, mx) in PARAMS_1110.items():
            if p.ref == cod and p.nome.lower().startswith(ini) and num(p.base) == antigo:
                p.base, p.minimo, p.maximo, mudou = str(novo), mn, mx, True
    contratos = {c["id"]: c for c in ref["contratos"]}
    for c in caso.contratos:
        if c.codigo == "C06" and (c.parte or "").startswith("Contador Formado S/S"):
            c.parte, mudou = contratos["C06"]["parte"], True
        if c.codigo == "C05" and "pagamento único em 24/02/2026" in (c.descricao or ""):
            c.descricao, mudou = contratos["C05"]["descricao"], True
    eventos = {e["id"]: e for e in ref["eventos"]}
    for e in caso.eventos:
        if e.codigo not in EVENTOS_1110:
            continue
        novo = eventos[e.codigo]
        antiga = EVENTOS_1110[e.codigo]
        if antiga and e.data == date.fromisoformat(antiga):
            e.data, mudou = date.fromisoformat(novo["data"]), True
        if e.codigo in DESCRICOES_ANTIGAS_1110 and e.descricao == DESCRICOES_ANTIGAS_1110[e.codigo]:
            e.descricao, mudou = novo["descricao"], True
    funcs = {f["nome"]: f for f in ref["funcionarios"]}
    for f in caso.funcionarios:
        if DEPENDENTES_FEV_ANTIGOS.get(f.nome) == f.dependentes_fev and f.nome in funcs:
            f.dependentes_fev, mudou = funcs[f.nome]["dependentes_fev"], True
    dados = dict(caso.dados or {})
    regras = dict(dados.get("folha_regras") or {})
    if "27,80%" in (regras.get("encargos") or ""):
        regras["encargos"] = ref["folha_regras"]["encargos"]
        dados["folha_regras"] = regras
        caso.dados, mudou = dados, True
    novas = {x["onde"]: x for x in ref["inconsistencias"]}
    for x in caso.inconsistencias:
        n = novas.get(x.onde)
        if n and x.status == "PENDENTE" and (n["status"] != "PENDENTE" or not x.decisao):
            x.status, x.decisao, x.descricao, mudou = n["status"], n.get("decisao"), n["descricao"], True
    return mudou


def aplicar_1110(db: Session) -> int:
    """Aplica as decisões de 11/10/2026 uma única vez e recalcula as empresas dos casos alterados."""
    if db.get(AjusteSistema, CHAVE_1110):
        return 0
    from .geracao import gerar
    from .models_dupla import EmpresaGerada

    ref = _base_json()
    alterados = [c for c in db.query(Caso).all() if _ajustar_caso_1110(c, ref)]
    db.flush()
    n_emp = 0
    for caso in alterados:
        for e in db.query(EmpresaGerada).filter_by(caso_id=caso.id).all():
            d = e.dupla
            base = (e.valores or {}).get("modo") == "caso-base"
            valores = gerar(caso, e.semente, d.rotulo, None if base else d.numero, base=base)
            valores["integrantes"] = (e.valores or {}).get("integrantes", [])
            e.valores = valores
            n_emp += 1
    db.add(AjusteSistema(chave=CHAVE_1110, detalhe=f"{len(alterados)} caso(s), {n_emp} empresa(s) recalculada(s)"))
    db.commit()
    return len(alterados)


# ---------------------------------------------------------------------------------------------------------------
# Análise completa de 11/10/2026: custos unitários com a precisão do exercício, salário mínimo da Ângela,
# datas das vendas ALPHA e novos itens da lista de inconsistências
CHAVE_1110B = "exercicio_analise_completa_2026_10_11"
CUSTOS_1110B = {"MP-A": (9.0867, 9.0867112), "MP-B": (11.2986, 11.2986347), "MS-Z": (10.06, 10.0600459),
                "MS-Q": (11.5536, 11.553644), "MS-R": (12.5751, 12.5750572), "MS-K": (13.2894, 13.28943795),
                "ME-H": (5.6589, 5.65893), "ALPHA": (19.6703, 19.6703463)}
CUSTO_EVENTO_1110B = {"J15": "ALPHA", "J30": "MP-A", "F05": "MP-B", "F22": "ME-H"}
DESCRICOES_1110B = {"J27": "boleto em 25/01", "F26": "boleto em 28/02"}
DECISOES_ANTIGAS_1110B = {
    "Conta garantida (C01)": "Decisão do professor (11/10/2026): novecentos e setenta mil reais.",
    "Leasing (C04, J24, F33)": "Decisão do professor (11/10/2026): liberação em 19/01, data do contrato.",
    "Arquiteto (C11, J23, F30)": "Decisão do professor (11/10/2026): contratação em 20/01.",
    "Recrutamento (C05, F41)": "Decisão do professor (11/10/2026): pagamento somente em 26/02, na emissão da NFS-e 345.",
    "Mútuo (C10, F27)": "Decisão do professor (11/10/2026): cessão de R$ 30.000,00 no caso-base (o valor da dupla está no contrato C10); texto do contrato mantido.",
    "Seguro (C09, J21)": "Decisão do professor (11/10/2026): 3ª e última parcela; vencimento em fim de semana é pago no próximo dia útil (19/01).",
    "Contabilidade (C06)": "Decisão do professor (11/10/2026): Contador Formado S/A; pagamento no dia 10 do mês seguinte (NFS-e 023 em 10/02; NFS-e 024 em 10/03).",
    "Comodatos (C07, C08)": "Decisão do professor (11/10/2026): contratos de R$ 410,00 (internet) e R$ 580,00 (celulares); as notas de telefonia de janeiro e fevereiro acompanham.",
    "Frete MP-A (J30)": "Decisão do professor (11/10/2026): frete CIF, a cargo do fornecedor; o CT-e não tem evento de pagamento (sem lançamento).",
    "NF 23.456 (J30, F37)": "Decisão do professor (11/10/2026): emissão em 24/01 e entrada em 26/01.",
    "Auto de infração (J29, F06)": "Decisão do professor (11/10/2026): pagamento em 05/02; redução de 70% da multa por pagamento no prazo, sem recurso; alíquota de 18%.",
    "Aplicações (J14, F07)": "Decisão do professor (11/10/2026): renda fixa (05/01) e CDB são aplicações diferentes; data em fim de semana vai para o próximo dia útil (12/01).",
    "Ar Frio (J08, F11)": "Decisão do professor (11/10/2026): emissão em 05/01 e entrada em 08/01; pagamento de 40% em 09/02.",
    "Vendas ALPHA (J27, J33, F26, F36, F44)": None,
    "Comissões (J16, J25, F08, F13)": "Decisão do professor (11/10/2026): recebimentos em atraso, sem juros e multa.",
    "Folha (funcionários)": "Decisão do professor (11/10/2026): idades de fevereiro iguais às de janeiro; salário de R$ 2.500,00 em janeiro (Marena).",
    "Energia e água (J03, F01, F02)": "Corrigido pelo professor no exercício revisado de 07/10/2026.",
    "Encargos (FPAS)": "Decisão do professor (11/10/2026): encargos de 28,80% (INSS + RAT 3% + Terceiros).",
    "Imobilizado": "Corrigido pelo professor no exercício revisado de 07/10/2026.",
    "Materiais secundários (F10)": None,
    "Balanço de 31/12/2025 (versão de 07/10)": "Decisão do professor (11/10/2026): ajustar os subtotais do Balanço; manter a depreciação de 10.408,33 na DRE."
}


def _ajustar_caso_1110b(caso: Caso, ref: dict) -> bool:
    from .caso_servico import fmt

    mudou = False
    for i in caso.itens:
        par = CUSTOS_1110B.get(i.codigo)
        if par and i.custo_base is not None and abs(i.custo_base - par[0]) < 1e-9:
            i.custo_base, mudou = par[1], True
    for p in caso.parametros:
        if p.escopo == "evento" and p.ref in CUSTO_EVENTO_1110B and p.nome.lower().startswith("custo unit"):
            antigo, novo = CUSTOS_1110B[CUSTO_EVENTO_1110B[p.ref]]
            if num(p.base) is not None and abs(num(p.base) - antigo) < 1e-9:
                p.base, mudou = fmt(novo), True
        if p.escopo == "contrato" and p.ref == "C10" and p.nome.lower().startswith("valor") and p.base == "30000":
            p.base, mudou = fmt(30000.0), True
    for f in caso.funcionarios:
        if f.nome == "Ângela Peruana" and f.salario_fev == 1530.0:
            f.salario_fev, mudou = 1621.0, True
    eventos = {e["id"]: e for e in ref["eventos"]}
    for e in caso.eventos:
        trecho = DESCRICOES_1110B.get(e.codigo)
        if trecho and (e.descricao or "").endswith(trecho):
            e.descricao, mudou = eventos[e.codigo]["descricao"], True
    novas = {x["onde"]: x for x in ref["inconsistencias"]}
    existentes = {x.onde: x for x in caso.inconsistencias}
    for onde, n in novas.items():
        x = existentes.get(onde)
        if x is None:
            if onde not in DECISOES_ANTIGAS_1110B and caso.inconsistencias:
                caso.inconsistencias.append(Inconsistencia(onde=onde, descricao=n["descricao"], decisao=n.get("decisao"),
                                                           status=n["status"]))
                mudou = True
            continue
        antiga = DECISOES_ANTIGAS_1110B.get(onde)
        if n.get("decisao") != x.decisao and (x.decisao == antiga or not x.decisao):
            x.status, x.decisao, mudou = n["status"], n.get("decisao"), True
    return mudou


def aplicar_1110b(db: Session) -> int:
    """Aplica as correções da análise completa (11/10/2026) uma única vez e recalcula as empresas."""
    if db.get(AjusteSistema, CHAVE_1110B):
        return 0
    from .geracao import gerar
    from .models_dupla import EmpresaGerada

    ref = _base_json()
    alterados = [c for c in db.query(Caso).all() if _ajustar_caso_1110b(c, ref)]
    db.flush()
    n_emp = 0
    for caso in alterados:
        for e in db.query(EmpresaGerada).filter_by(caso_id=caso.id).all():
            d = e.dupla
            base = (e.valores or {}).get("modo") == "caso-base"
            valores = gerar(caso, e.semente, d.rotulo, None if base else d.numero, base=base)
            valores["integrantes"] = (e.valores or {}).get("integrantes", [])
            e.valores = valores
            n_emp += 1
    db.add(AjusteSistema(chave=CHAVE_1110B, detalhe=f"{len(alterados)} caso(s), {n_emp} empresa(s) recalculada(s)"))
    db.commit()
    return len(alterados)
