"""Tutor socrático da dupla (Etapa 6).

Usa a IA local instalada no servidor (Ollama ou qualquer servidor compatível com a API da OpenAI),
configurada no .env do VPS:
    TUTOR_LLM_URL   ex.: http://host.docker.internal:11434  (Ollama)  ou  http://ia:8000/v1 (compatível OpenAI)
    TUTOR_LLM_MODEL ex.: llama3.1:8b
    TUTOR_LLM_KEY   (opcional) chave, se o servidor exigir
Sem IA configurada ou fora do ar, o tutor responde com roteiros de perguntas por tipo de evento.

Garantias pedagógicas:
  - o tutor NUNCA recebe o gabarito: não há como "vazar" a resposta;
  - antes do fechamento mensal, não confirma se lançamento/valor está certo;
  - depois do fechamento, recebe apenas a dica da correção daquele evento (a mesma que a dupla vê).
"""
from __future__ import annotations

import os
import re

import httpx

from . import plano_contas as pc

LIMITE_DIARIO = 40  # perguntas por dupla por dia

SISTEMA = """Você é o Tutor do LABCONT-AI, monitor da disciplina Laboratório de Prática Contábil (UFC).
A dupla está escriturando os fatos de {mes_nome}/2026 da sua empresa simulada (indústria e comércio, Lucro Real, Fortaleza-CE).

Como você ajuda:
- Use o método socrático: devolva perguntas e pistas que levem a dupla a raciocinar sobre o documento, a natureza da operação, os tributos envolvidos e as contas afetadas.
- Baseie as explicações na "Base normativa" do contexto e cite a fonte (ex.: "Lei 6.404/76, art. 193"). Não invente artigos.
- Explique conceitos e normas quando pedirem (CPC, legislação do ICMS do Ceará, IPI, PIS/COFINS não cumulativos, IRPJ/CSLL, folha de pagamento) e mostre onde procurar no documento.
- Pode demonstrar um método com números DIFERENTES dos da dupla (ex.: "se uma nota de R$ 1.000,00 tivesse ICMS de 12%...").

Plano de contas da empresa: 1.01 Ativo Circulante; 1.07 Ativo não Circulante; 2.01 Passivo Circulante; 2.03 Passivo não Circulante;
2.07 Patrimônio Líquido (capital, reservas, lucros acumulados); 3 Resultado (receitas, custos e despesas).
Use sempre o grupo correto ao citar uma conta (ex.: Lucros Acumulados é do Patrimônio Líquido, não do Ativo).

Regras que você nunca quebra:
1. Não entregue lançamentos prontos (pares de contas a débito e a crédito com os valores da dupla) nem o valor final calculado com os números da dupla.
2. {regra_correcao}
3. Se pedirem a resposta pronta, recuse com gentileza e devolva uma pergunta-guia.
4. Se a pergunta fugir da disciplina, redirecione para o exercício.
5. Responda em português do Brasil, com no máximo 150 palavras, e termine com uma pergunta para a dupla."""

REGRA_ANTES = ("Não diga se um lançamento, conta ou valor da dupla está certo ou errado: a correção só acontece "
               "no fechamento mensal. Ajude a dupla a conferir sozinha (fonte do valor, débitos = créditos, natureza das contas).")
REGRA_DEPOIS = ("O mês já foi enviado e corrigido. Você pode comentar a correção informada no contexto e ajudar a dupla "
                "a entender o erro, sem entregar o lançamento correto.")

# ------------------------------------------------------------------ roteiros (sem IA)
ROTEIROS = {
    "compra": ["Qual é o CFOP da nota e o que ele diz sobre a operação (revenda, industrialização ou uso)?",
               "Que tributos estão destacados no documento e quais deles a empresa pode recuperar, considerando a destinação do bem?",
               "Quem paga o frete (CIF ou FOB) e como isso afeta o custo de aquisição?",
               "Quanto foi pago à vista e quanto ficou para pagar? Em que conta fica a obrigação?"],
    "venda": ["Como o mark-up chega ao preço de venda a partir do custo médio da mercadoria ou do custo de produção?",
              "A venda é para dentro do estado ou para outro estado? O comprador é contribuinte ou consumidor final?",
              "Quais tributos incidem sobre essa venda e qual é a base de cálculo de cada um?",
              "Além da receita, que outro registro é necessário para a mercadoria que saiu do estoque?"],
    "servico": ["O documento é de serviço tomado ou prestado pela empresa?",
                "Há retenções na fonte (IRRF, CSRF, INSS, ISS)? Quem é o responsável por recolhê-las?",
                "A despesa pertence a qual competência e a qual área da empresa?"],
    "pagamento": ["Onde essa obrigação estava registrada antes do pagamento (balanço de 31/12/2025 ou lançamento de um mês anterior)?",
                  "O pagamento quita a dívida inteira ou só uma parte? Há juros, multa ou desconto?"],
    "folha": ["Quais verbas compõem a remuneração de cada empregado e quais descontos incidem sobre ela?",
              "Que encargos são da empresa (INSS patronal, RAT, Terceiros, FGTS) e quais são do empregado?",
              "Como ficam as provisões de férias e 13º salário e os encargos sobre elas?"],
    "financeiro": ["A operação é uma aplicação, um empréstimo ou um arrendamento? Que norma orienta o registro?",
                   "Os juros ou rendimentos são reconhecidos em que momento (regime de competência)?",
                   "Como separar a parte de curto e a de longo prazo?"],
    "capital": ["O que muda no patrimônio líquido quando o sócio integraliza o capital subscrito?",
                "Onde estava registrado o capital a integralizar no balanço de 31/12/2025 e por qual meio o sócio integralizou?"],
    "resultado": ["Qual foi o lucro líquido de 2025 e onde ele aparece no balanço de 31/12/2025 e na DRE?",
                  "Em que ordem a Lei 6.404/76 manda deduzir as participações (arts. 189 e 190) antes de calcular a reserva legal?",
                  "Qual é a base e o limite da reserva legal (art. 193)? E sobre que base se calculam os dividendos mínimos (art. 202)?",
                  "O que o estatuto/contrato social diz sobre a reserva estatutária? Para onde vai o saldo não destinado?"],
    "recebimento": ["Onde esse direito foi registrado quando a receita foi reconhecida?",
                    "O valor recebido é igual ao valor do título? Houve retenção, desconto ou juros?"],
    "apuracao": ["Quais créditos e débitos de ICMS, PIS e COFINS foram registrados no mês?",
                 "Como se calcula o IRPJ e a CSLL por estimativa sobre a receita bruta?",
                 "Quando o saldo é credor, o que acontece com ele?"],
    "producao": ["Quais itens da ficha técnica cada produto consome e quanto do estoque de cada insumo foi requisitado?",
                 "Por qual custo os insumos saem do estoque (custo médio na data da requisição)?",
                 "O que é custo direto e o que é custo indireto nesta produção? Qual a base de rateio definida no exercício?",
                 "Em que momento os custos saem de Produtos em Elaboração e vão para Produtos Acabados?"],
    "geral": ["Qual documento comprova esse fato e qual é a data de competência?",
              "Que contas do plano são afetadas e qual é a natureza de cada uma (devedora ou credora)?",
              "Os débitos somam o mesmo que os créditos?"],
}
GRUPO_EVENTO = {
    "J08": "compra", "J09": "compra", "J15": "compra", "J30": "compra", "J27": "venda",
    "J02": "servico", "J03": "servico", "J05": "servico", "J16": "servico", "J23": "servico", "J26": "servico", "J39": "servico",
    "J06": "pagamento", "J07": "pagamento", "J10": "pagamento", "J11": "pagamento", "J12": "pagamento", "J13": "pagamento",
    "J17": "pagamento", "J21": "pagamento", "J22": "pagamento", "J28": "pagamento", "J31": "pagamento", "J32": "pagamento",
    "J35": "pagamento", "J38": "pagamento", "J25": "recebimento", "J33": "recebimento",
    "J18": "folha", "J36": "folha", "J37": "folha", "J04": "financeiro", "J14": "financeiro", "J24": "financeiro",
    "TES": "financeiro", "AJ": "financeiro", "J20": "capital", "J34": "capital", "J01": "resultado", "J40": "apuracao",
    "J19": "geral", "J29": "geral",
    # fevereiro
    "F05": "compra", "F10": "compra", "F22": "compra", "F28": "compra", "F04": "venda", "F26": "venda", "F34": "venda",
    "F36": "venda", "F01": "servico", "F02": "servico", "F03": "servico", "F08": "servico", "F32": "servico", "F41": "servico",
    "F45": "servico", "F06": "pagamento", "F09": "pagamento", "F11": "pagamento", "F12": "pagamento", "F14": "pagamento",
    "F16": "pagamento", "F17": "pagamento", "F18": "pagamento", "F19": "pagamento", "F23": "pagamento", "F24": "pagamento",
    "F29": "pagamento", "F30": "pagamento", "F31": "pagamento", "F35": "pagamento", "F37": "pagamento", "F40": "pagamento",
    "F42": "pagamento", "F43": "pagamento", "F46": "pagamento", "F13": "recebimento", "F44": "recebimento",
    "F20": "folha", "F38": "folha", "F39": "folha", "F07": "financeiro", "F27": "financeiro", "F33": "financeiro",
    "F47": "financeiro", "FTES": "financeiro", "FAJ": "financeiro", "F15": "capital", "F25": "capital", "F48": "apuracao",
    "F21": "geral", "FP1": "producao", "FP2": "producao",
}


def fontes(normas: list | None) -> str:
    """Linha de fontes acrescentada pelo sistema à resposta (não depende do modelo)."""
    if not normas:
        return ""
    return "\n\nPara consultar: " + "; ".join(f"{n.fonte} ({n.titulo})" for n in normas)


def roteiro(evento: str | None, n_anteriores: int = 0) -> str:
    perguntas = ROTEIROS.get(GRUPO_EVENTO.get((evento or "").upper(), "geral"), ROTEIROS["geral"])
    p = perguntas[n_anteriores % len(perguntas)]
    return ("O tutor com IA está indisponível no momento; enquanto isso, um roteiro para orientar a dupla:\n\n"
            f"{p}\n\nReleia o documento do evento e anote a resposta antes de lançar.")


# ------------------------------------------------------------------ contexto
def _fmt(v) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _doc_texto(d: dict) -> str:
    partes = [f"{d['titulo']} nº {d.get('numero') or '-'} de {d['data'][8:10]}/{d['data'][5:7]}",
              f"emitente: {d['emitente']['nome']} ({d['emitente']['uf']})"]
    for k in ("cfop", "natureza", "transporte", "servico", "classe", "obs", "infracao", "pagamento", "tomador"):
        if d.get(k):
            partes.append(f"{k}: {d[k]}")
    for i in d.get("itens", []) or []:
        partes.append(f"item: {i.get('descricao')} qtd {i.get('quantidade')} "
                      f"{('unit ' + _fmt(i['unitario'])) if i.get('unitario') else 'preço a calcular'}"
                      f"{(' ICMS ' + str(i['aliq_icms']) + '%') if i.get('aliq_icms') is not None else ''}"
                      f"{(' IPI ' + str(i['aliq_ipi']) + '%') if i.get('aliq_ipi') else ''}")
    for k, rot in (("produtos", "valor dos produtos"), ("desconto", "desconto"), ("icms", "ICMS destacado"), ("ipi", "IPI"),
                   ("total", "total"), ("valor", "valor"), ("materiais", "materiais"), ("mao_de_obra", "mão de obra"),
                   ("base", "base de cálculo"), ("multa", "multa")):
        v = d.get(k)
        if isinstance(v, (int, float)) and v:
            partes.append(f"{rot}: {_fmt(v)}")
    for n, venc, v in d.get("duplicatas", []) or []:
        partes.append(f"parcela {n} venc. {venc[8:10]}/{venc[5:7]}: {_fmt(v) if v else 'a calcular'}")
    for k, v in d.get("clausulas", []) or []:
        partes.append(f"{k}: {v}")
    return "; ".join(partes)


def classe_conta(conta: str) -> str:
    """Ex.: 'Lucros Acumulados (Patrimônio Líquido; natureza credora)' — evita confusões do modelo sobre grupos."""
    info = pc.CONTAS.get(conta, {})
    sint = pc.sinteticas_de(conta) if conta in pc.CONTAS else []
    grupos = [pc.SINTETICAS[c] for c in sint if c.count(".") == 1 and c in pc.SINTETICAS]
    nat = {"D": "devedora", "C": "credora"}.get(info.get("natureza"), "")
    return f"{info.get('nome', conta)} ({'; '.join(x for x in (grupos[0] if grupos else '', 'natureza ' + nat if nat else '') if x)})"


def contexto(evento: dict | None, docs: list[dict], lancs, regras: list[str], correcao: dict | None,
             com_valores: bool | None = None, normas: list | None = None, mes: str = "2026-01") -> str:
    """com_valores: mostra os valores dos lançamentos da dupla (só depois do fechamento). Antes, vão só contas e lados,
    para a IA não repetir o valor digitado como se fosse a resposta."""
    if com_valores is None:
        com_valores = correcao is not None
    linhas = []
    if evento:
        linhas.append(f"Evento {evento['codigo']} ({evento['data']:%d/%m/%Y}): {evento['descricao']}")
        evd = [d for d in docs if d["evento"] == evento["codigo"]]
        if evd:
            linhas.append("Documentos do evento: " + " | ".join(_doc_texto(d) for d in evd))
        else:
            linhas.append("Este evento não tem documento próprio; os valores estão no balanço de 31/12/2025 ou nos contratos.")
        meus = [l for l in lancs if l.evento == evento["codigo"]]
        if meus:
            for l in meus:
                ps = "; ".join(f"{'débito' if p.natureza == 'D' else 'crédito'} em {classe_conta(p.conta)}"
                               + (f" {_fmt(p.valor)}" if com_valores else "") for p in l.partidas)
                linhas.append(f"Lançamento da dupla ({l.historico}): {ps}"
                              + ("" if com_valores else " [valores omitidos: não comente nem calcule valores da dupla]"))
        else:
            linhas.append("A dupla ainda não lançou este evento.")
    if regras:
        linhas.append("Regras do caso definidas pelo professor: " + " ".join(regras))
    if normas:
        linhas.append("Base normativa (explique a partir destas fontes e cite a fonte ao usar):")
        for n in normas:
            linhas.append(f"- [{n.fonte}] {n.titulo}: {n.texto}")
    if correcao:
        linhas.append(f"Correção do fechamento para este evento: {correcao.get('nivel')} — {correcao.get('dica')}")
    return "\n".join(linhas)


# ------------------------------------------------------------------ IA local
def configuracao() -> dict:
    return {"url": (os.getenv("TUTOR_LLM_URL") or "").rstrip("/"), "modelo": os.getenv("TUTOR_LLM_MODEL") or "",
            "chave": os.getenv("TUTOR_LLM_KEY") or ""}


def _compat_openai(url: str) -> bool:
    return bool(re.search(r"/v1$", url))


async def chamar_ia(mensagens: list[dict], timeout: float = 90.0) -> str | None:
    cfg = configuracao()
    if not cfg["url"] or not cfg["modelo"]:
        return None
    cab = {"Authorization": f"Bearer {cfg['chave']}"} if cfg["chave"] else {}
    try:
        async with httpx.AsyncClient(timeout=timeout) as cli:
            if _compat_openai(cfg["url"]):
                r = await cli.post(f"{cfg['url']}/chat/completions", headers=cab,
                                   json={"model": cfg["modelo"], "messages": mensagens, "temperature": 0.2, "max_tokens": 450})
                r.raise_for_status()
                return (r.json()["choices"][0]["message"]["content"] or "").strip() or None
            r = await cli.post(f"{cfg['url']}/api/chat", headers=cab,
                               json={"model": cfg["modelo"], "messages": mensagens, "stream": False,
                                     "options": {"temperature": 0.2, "num_predict": 450, "num_ctx": 8192}})
            r.raise_for_status()
            return ((r.json().get("message") or {}).get("content") or "").strip() or None
    except Exception:
        return None


async def status_ia() -> dict:
    """Situação da IA local para o painel do professor (nunca devolve a chave)."""
    cfg = configuracao()
    pub = {"url": cfg["url"], "modelo": cfg["modelo"], "chave_definida": bool(cfg["chave"])}
    if not cfg["url"]:
        return {"ok": False, "motivo": "TUTOR_LLM_URL não configurada no .env do servidor", "modelos": [], **pub}
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            if _compat_openai(cfg["url"]):
                r = await cli.get(f"{cfg['url']}/models", headers={"Authorization": f"Bearer {cfg['chave']}"} if cfg["chave"] else {})
                modelos = [m.get("id") for m in r.json().get("data", [])]
            else:
                r = await cli.get(f"{cfg['url']}/api/tags")
                modelos = [m.get("name") for m in r.json().get("models", [])]
        ok = bool(cfg["modelo"]) and any(cfg["modelo"] == m or (m or "").startswith(cfg["modelo"]) for m in modelos)
        return {"ok": ok, "modelos": modelos, "motivo": "" if ok else "modelo não encontrado no servidor de IA", **pub}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "motivo": f"servidor de IA inacessível ({type(e).__name__})", "modelos": [], **pub}


# ------------------------------------------------------------------ filtro de saída
# Modelos pequenos nem sempre obedecem ao prompt. Antes de mostrar a resposta, o código confere:
#   - valores monetários que não estão nos documentos do evento nem na pergunta (ex.: o valor digitado pela dupla);
#   - julgamentos "está certo/errado" antes do fechamento.
_NUM = re.compile(r"(?<![\d/])(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+,\d{1,2})(?![\d/])")
_EXEMPLOS = {float(m * 10 ** k) for k in range(0, 7) for m in (1, 2, 5)}  # números redondos de exemplo
_JULGA = re.compile(r"\b(est[áa]|estão|ficou|ficaram|parece|parecem)\s+(?:\w+\s+)?(corret[oa]s?|cert[oa]s?|errad[oa]s?|incorret[oa]s?)\b"
                    r"|\b(valor|lançamento|resposta)\s+(corret[oa]|cert[oa])\s+(é|seria|fica)", re.I)


def _numeros(txt: str) -> set[float]:
    out = set()
    for m in _NUM.findall(txt or ""):
        try:
            out.add(round(float(m.replace(".", "").replace(",", ".")), 2))
        except ValueError:
            pass
    return out


def violacoes(resposta: str, permitido: str, fechado: bool) -> list[str]:
    motivos = []
    extras = sorted(v for v in _numeros(resposta) - _numeros(permitido) if v not in _EXEMPLOS)
    if extras:
        motivos.append("citou valores que não estão nos documentos (" + ", ".join(_fmt(v) for v in extras[:3]) + ")")
    if not fechado and _JULGA.search(resposta or ""):
        motivos.append("julgou se o lançamento ou valor está certo/errado antes do fechamento")
    return motivos


LEMBRETE = ("\n\n(Lembrete ao tutor: não informe nem calcule valores com os números da dupla, não diga se algo está "
            "certo ou errado{extra}; dê pistas, cite onde procurar e termine com uma pergunta.)")


async def responder(pergunta: str, ctx: str, historico: list[tuple[str, str]], fechado: bool,
                    evento: str | None = None) -> tuple[str, str]:
    """Devolve (texto, origem). origem = 'ia' ou 'roteiro'."""
    mes_nome = ("fevereiro" if (evento or "").upper().startswith("F") else "janeiro") if evento else "janeiro e fevereiro"
    sistema = SISTEMA.format(regra_correcao=REGRA_DEPOIS if fechado else REGRA_ANTES, mes_nome=mes_nome)
    msgs = [{"role": "system", "content": sistema + "\n\nContexto da dupla:\n" + ctx}]
    for papel, texto in historico[-6:]:
        msgs.append({"role": "user" if papel == "aluno" else "assistant", "content": texto})
    lembrete = LEMBRETE.format(extra="" if not fechado else " além do que a correção informa")
    msgs.append({"role": "user", "content": pergunta + lembrete})
    n_tutor = sum(1 for p, _ in historico if p == "tutor")
    texto = await chamar_ia(msgs)
    if not texto:
        return roteiro(evento, n_tutor), "roteiro"
    permitido = ctx + "\n" + pergunta
    motivos = violacoes(texto, permitido, fechado)
    if not motivos:
        return texto, "ia"
    # uma segunda tentativa, explicando o problema
    msgs = msgs + [{"role": "assistant", "content": texto},
             {"role": "user", "content": "Sua resposta quebrou as regras: " + "; ".join(motivos) +
              ". Reescreva sem nenhum valor calculado e sem julgar o lançamento: só pistas e uma pergunta-guia."}]
    texto2 = await chamar_ia(msgs)
    if texto2 and not violacoes(texto2, permitido, fechado):
        return texto2, "ia"
    perguntas = ROTEIROS.get(GRUPO_EVENTO.get((evento or "").upper(), "geral"), ROTEIROS["geral"])
    return ("Não posso informar valores nem conferir o lançamento" + ("" if fechado else " antes do fechamento do mês") +
            ", mas posso ajudar a dupla a chegar lá.\n\n" + perguntas[n_tutor % len(perguntas)]), "filtro"
