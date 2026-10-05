"""Gera docs/PARAMETRIZACAO.md a partir de dados/caso_base/eh0012_2026_2.json."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[2]
d = json.loads((R / "dados/caso_base/eh0012_2026_2.json").read_text(encoding="utf-8"))

def brl(v):
    if isinstance(v, (int, float)):
        if isinstance(v, float):
            casas = 4 if abs(round(v, 2) - v) > 1e-9 else 2
            s = f"{v:,.{casas}f}"
        else:
            s = f"{v:,}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    return str(v)

def faixa(p):
    if "min" in p:
        un = p.get("unidade", "")
        pre = "R$ " if un == "R$" else ""
        suf = "" if un == "R$" else f" {un}"
        return f"{pre}{brl(p['min'])} a {pre}{brl(p['max'])}{suf} (passo {brl(p['passo'])})"
    return p.get("regra", "—")

L = []
a = L.append
a("# Parametrização do caso EH0012 (2026.2)\n")
a("> Documento gerado a partir de `dados/caso_base/eh0012_2026_2.json` (rode `python dados/caso_base/gerar_caso_base.py` e depois `gerar_doc.py`). "
  "As faixas são **propostas** para validação pelos professores da disciplina.\n")
a("## Como ler\n")
a("- **Base:** valor do caso original (empresa LAB).\n- **Faixa:** intervalo em que o valor de cada dupla será sorteado, com o passo de arredondamento.\n"
  "- **Derivado:** valor calculado pelo sistema a partir de outros parâmetros (saldos, contratos, folha, produção). Não é sorteado, mas muda junto com eles.\n"
  "- **Datas:** permanecem fixas em todas as duplas, para preservar o calendário de vencimentos e apurações.\n")
a("## Resumo\n")
ev = d["eventos"]
a(f"| Elemento | Itens | Parâmetros variáveis |\n|---|---|---|")
a(f"| Contratos | {len(d['contratos'])} | {sum(len(c['parametros']) for c in d['contratos'])} |")
a(f"| Funcionários (folha) | {len(d['funcionarios'])} empregados + 3 sócios com pró-labore | salário, HE, comissão, dependentes, pró-labore |")
a(f"| Produção | 2 produtos, 7 insumos, 1 mercadoria | quantidades, coeficientes, custos, margem |")
a(f"| Eventos | {len(ev)} ({sum(e['natureza']=='V' for e in ev)} com valores variáveis, {sum(e['natureza']=='D' for e in ev)} derivados) | ver seção 4 |\n")

a("## 1. Contratos\n")
for c in d["contratos"]:
    a(f"### {c['id']} · {c['tipo']}\n**Parte:** {c['parte']} · **Início:** {c['inicio']}  \n{c['descricao']}\n")
    a("| Parâmetro | Base | Faixa proposta |\n|---|---|---|")
    for p in c["parametros"]:
        a(f"| {p['nome']} | {brl(p['base'])} {'' if p.get('unidade')=='R$' else p.get('unidade','')} | {faixa(p)}{(' — ' + p['regra']) if p.get('regra') and 'min' in p else ''} |")
    a(f"\nEventos ligados: {', '.join(c['eventos'])}\n")

a("## 2. Folha de pagamento e funcionários\n")
r = d["folha_regras"]
a("**Regras fixas do caso:**\n")
for k, v in r.items():
    a(f"- **{k.replace('_', ' ')}:** {v if not isinstance(v, dict) else '; '.join(f'{x}: {y}' for x, y in v.items())}")
a("\n**Quadro de pessoal:** janeiro 5 empregados (3 Adm, 2 Com); fevereiro 15 (3 Adm, 3 Com, 7 MOD - 4 em X e 3 em Y, 2 MOI). Admissões em 01/02.\n")
a("| Setor | Empregado | Admissão | Salário jan | Salário fev | HE fev | Comissão fev | Dependentes fev |\n|---|---|---|---|---|---|---|---|")
for f in d["funcionarios"]:
    a(f"| {f['setor']} | {f['nome']} | {f['admissao']} | {brl(f['salario_jan']) if f['salario_jan'] else '—'} | {brl(f['salario_fev']) if f['salario_fev'] else '**sem valor**'} | {brl(f['he_fev']) if f['he_fev'] else '—'} | {brl(f['comissao_fev']) if f['comissao_fev'] else '—'} | {f['dependentes_fev']} |")
a("\n**Sócios (pró-labore):**\n\n| Sócio | Função | Cotas | A integralizar | Pró-labore jan | Pró-labore fev |\n|---|---|---|---|---|---|")
for s in d["socios"]:
    a(f"| {s['nome']} | {s['funcao']} | {brl(s['cotas'])} | {brl(s['a_integralizar'])} | {brl(s['pro_labore_jan'])} | {brl(s['pro_labore_fev'])} |")
a("\n| Parâmetro | Base | Faixa proposta |\n|---|---|---|")
for p in d["parametros_folha"] + d["parametros_socios"]:
    a(f"| {p['nome']} | {brl(p['base'])} | {faixa(p)}{(' — ' + p['regra']) if p.get('regra') and 'min' in p else ''} |")

a("\n## 3. Produção, ficha técnica e mercadoria\n")
a("| Código | Item | Tipo | NCM | Custo unitário base | Faixa |\n|---|---|---|---|---|---|")
for i in d["itens"]:
    a(f"| {i['codigo']} | {i['descricao']} | {i['tipo']} | {i['ncm']} | {brl(i['custo_base']) if i['custo_base'] else '—'} | {('R$ ' + brl(i['custo_min']) + ' a R$ ' + brl(i['custo_max'])) if i['custo_min'] else 'apurado pelo custeio'} |")
ft = d["ficha_tecnica"]
ins = ["MP-A", "MP-B", "MS-Z", "MS-Q", "MS-R", "MS-K", "ME-H"]
a("\n**Ficha técnica (unidades de insumo por unidade de produto):**\n")
a("| Produto | " + " | ".join(ins) + " |\n|---|" + "---|" * len(ins))
for prod, comp in ft.items():
    a(f"| {prod} | " + " | ".join(str(comp.get(x, '—')) for x in ins) + " |")
pp = d["plano_producao"]
a(f"\n**Plano de produção ({pp['mes']}):** X = {brl(pp['X'])} un; Y = {brl(pp['Y'])} un. Início: {pp['inicio']}; duração: {pp['duracao']}.\n")
a("**Coerência verificada no caso original:** cada compra cobre a necessidade da ficha técnica com uma sobra de 140 a 280 unidades "
  "(MP-A: necessidade 133.300; compra 133.900 − devolução 320 = 133.580). As vendas de X (19.190) e Y (18.520) correspondem a 99,4% e 99,0% da produção. "
  "A mercadoria ALPHA fecha fevereiro com 125 unidades (620 + 18.075 − 8.200 − 40 − 10.400 + 70).\n")
m = d["markup"]
a(f"**Mark-up:** ICMS {m['ICMS']}% + PIS {m['PIS']}% + COFINS {m['COFINS']}% + margem de contribuição {m['margem_contribuicao']}% → divisor {m['divisor']} (multiplicador {m['multiplicador']}). "
  f"Margem variável: {faixa(m['parametro'])}.\n")
a("| Parâmetro de produção | Base | Faixa proposta |\n|---|---|---|")
for p in d["parametros_producao"]:
    a(f"| {p['nome']} | {brl(p['base'])} | {faixa(p)}{(' — ' + p['regra']) if p.get('regra') and 'min' in p else ''} |")

a("\n## 4. Eventos\n")
a("Natureza: **V** = possui valores sorteados por dupla; **D** = derivado (calculado pelo sistema); P01/P02 são eventos de produção implícitos nas regras do caso.\n")
for mes, rot in (("2026-01", "Janeiro/2026"), ("2026-02", "Fevereiro/2026")):
    a(f"### {rot}\n\n| ID | Data | Grupo | Evento | Nat. | Parâmetros variáveis (base → faixa) |\n|---|---|---|---|---|---|")
    for e in sorted([e for e in ev if e["data"].startswith(mes)], key=lambda e: (e["data"], e["id"])):
        ps = "; ".join(f"{p['nome']}: {brl(p['base'])} → {faixa(p)}" for p in e.get("parametros", []))
        if e.get("contrato") and not ps:
            ps = f"ver contrato {e['contrato']}"
        if e.get("obs"):
            ps = (ps + " · " if ps else "") + f"*{e['obs']}*"
        dd = e["data"][8:10] + "/" + e["data"][5:7]
        a(f"| {e['id']} | {dd} | {e['grupo']} | {e['descricao']} | {e['natureza']} | {ps or '—'} |")
    a("")

a("## 5. Regras de coerência para a geração por dupla\n")
for t in [
    "Quantidades compradas de insumos = necessidade da ficha técnica × produção + sobra (100 a 300 un). Para MP-A, soma-se a quantidade devolvida.",
    "Vendas de mercadoria e de produtos nunca superam o estoque disponível na data (custo médio ponderado móvel).",
    "Saldos iniciais ligados a contratos (seguro a apropriar, fornecedores de comodato e contabilidade) e à folha são recalculados; a conta Banco Rico fecha o balanço.",
    "Valores monetários arredondados ao passo indicado; custos unitários com 4 casas decimais e total da nota em centavos.",
    "Datas, CFOPs, UFs de origem e destino e regras tributárias ficam fixos: a variação é numérica, e a dificuldade técnica é a mesma para todas as duplas.",
    "Cada dupla recebe uma semente de sorteio registrada. Com ela o caso pode ser regerado e o gabarito recalculado a qualquer momento.",
    "Equivalência: os sorteios usam faixas próximas da base (cerca de ±15% a ±20%), mantendo o porte da empresa e o volume de lançamentos.",
]:
    a(f"- {t}")

a("\n## 6. Inconsistências encontradas no caso original\n")
a("Foram encontradas no texto do exercício. Precisam de decisão docente antes de virarem regra no sistema.\n")
a("| # | Onde | Descrição |\n|---|---|---|")
for i, x in enumerate(d["inconsistencias"], 1):
    a(f"| {i} | {x['onde']} | {x['descricao']} |")
(R / "docs/PARAMETRIZACAO.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("ok", len(L), "linhas")
