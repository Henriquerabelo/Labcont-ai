"""Módulo 5 do memorial · Painel de Gestão e Learning Analytics (Etapa 7b).

Tudo é calculado a partir dos dados que o próprio sistema já registra — nada de planilha:
  lançamentos (quando e por quem), auditoria contra o gabarito, fechamentos enviados, conversas com o tutor,
  acessos e o histórico de ações.

Saídas por turma:
  - visão panorâmica por grupo (progresso, % correto — oficial ou prévia —, situação de janeiro, atividade);
  - alertas precoces (sem acesso, inatividade, progresso abaixo da turma, estagnação em evento crítico,
    prévia baixa, insistência por respostas prontas, participação desigual entre integrantes);
  - matriz de calor (evento × grupo) e dificuldades por tema e por conta contábil;
  - engajamento diário (30 dias);
  - nota preliminar de janeiro por critério objetivo (para homologação pelo professor).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import plano_contas as pc
from .auditoria import auditar, eventos_ate, eventos_janeiro, eventos_mes
from .periodos import do_mes
from .db import Base
from .gabarito import gerar_gabarito
from .models import Turma
from .models_dupla import Dupla
from .models_escrita import DuplaAcesso, Lancamento, TutorMensagem, fechamento_ativo

# --------------------------------------------------------------------- parâmetros pedagógicos (transparentes)
PESOS_NIVEL = {"correto": 1.0, "valor": 0.5, "conta": 0.0, "pendente": 0.0}  # critério da nota preliminar
DIAS_INATIVO = 7
EVENTOS_CRITICOS = {"J18": "folha de janeiro", "J24": "leasing (CPC 06)", "J27": "venda pelo mark-up",
                    "J30": "compra de matéria-prima com IPI", "J40": "apuração dos tributos", "TES": "tesouraria",
                    "F05": "compra de MP-B com desconto condicional", "F20": "folha de fevereiro", "F33": "parcela do leasing (SAC)",
                    "F34": "venda dos produtos X e Y", "F48": "apuração de fevereiro", "FTES": "tesouraria de fevereiro"}
TEMAS = [
    ("Patrimônio líquido e destinação", ["J01", "J20", "J34"]),
    ("Compras e tributos recuperáveis", ["J08", "J09", "J15", "J30"]),
    ("Serviços, consumo e retenções", ["J02", "J03", "J05", "J11", "J16", "J23", "J26", "J39"]),
    ("Folha, encargos e benefícios", ["J06", "J07", "J18", "J28", "J36", "J37"]),
    ("Pagamentos e recebimentos", ["J10", "J12", "J13", "J17", "J21", "J22", "J25", "J31", "J32", "J33", "J35", "J38"]),
    ("Financeiro, leasing e tesouraria", ["J04", "J14", "J24", "TES", "AJ"]),
    ("Venda e custo (mark-up)", ["J27"]),
    ("Imobilizado e depreciação", ["J19"]),
    ("Autuação fiscal", ["J29"]),
    ("Apuração dos tributos", ["J40"]),
    # fevereiro
    ("Patrimônio líquido e partes relacionadas", ["F15", "F25", "F27"]),
    ("Compras de insumos e estoques (custo médio)", ["F05", "F10", "F22", "F23", "F28", "F35"]),
    ("Utilidades, serviços e retenções", ["F01", "F02", "F03", "F08", "F32", "F41", "F45"]),
    ("Folha, encargos e benefícios (fev.)", ["F09", "F12", "F20", "F31", "F38", "F39"]),
    ("Pagamentos e recebimentos (fev.)", ["F06", "F11", "F13", "F14", "F16", "F17", "F18", "F19", "F24", "F29", "F30",
                                          "F37", "F40", "F42", "F43", "F44", "F46"]),
    ("Financeiro, leasing e tesouraria (fev.)", ["F07", "F33", "F47", "FTES", "FAJ"]),
    ("Vendas, devoluções e custo dos produtos", ["F04", "F26", "F34", "F36"]),
    ("Depreciação e custos de produção", ["F21"]),
    ("Apuração de fevereiro", ["F48"]),
]
TEMA_DO_EVENTO = {ev: tema for tema, evs in TEMAS for ev in evs}


class NotaPeriodo(Base):
    """Nota de um aluno em um período (janeiro), proposta pelo sistema e homologada pelo professor."""
    __tablename__ = "notas_periodo"
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"), index=True)
    dupla_id: Mapped[int | None] = mapped_column(ForeignKey("duplas.id", ondelete="SET NULL"))
    discente_id: Mapped[int] = mapped_column(ForeignKey("discentes.id", ondelete="CASCADE"))
    periodo: Mapped[str] = mapped_column(String(7), default="2026-01")
    nota_sistema: Mapped[float | None] = mapped_column(Float)
    ajuste: Mapped[float] = mapped_column(Float, default=0.0)
    observacao: Mapped[str | None] = mapped_column(Text)
    homologada: Mapped[bool] = mapped_column(Boolean, default=False)
    homologada_em: Mapped[datetime | None] = mapped_column(DateTime)
    homologada_por: Mapped[str | None] = mapped_column(String(160))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    @property
    def nota_final(self) -> float | None:
        if self.nota_sistema is None:
            return None
        return round(min(10.0, max(0.0, self.nota_sistema + (self.ajuste or 0))), 1)


def nota_por_niveis(niveis: dict[str, str], total: int) -> float:
    if not total:
        return 0.0
    pontos = sum(PESOS_NIVEL.get(n, 0) for n in niveis.values())
    return round(10 * pontos / total, 1)


# --------------------------------------------------------------------- análise da turma
def _ultima(*datas):
    ds = [d for d in datas if d]
    return max(ds) if ds else None


def analisar_turma(db: Session, tid: int, agora: datetime | None = None, mes: str = "2026-01") -> dict:
    agora = agora or datetime.now()
    t = db.get(Turma, tid)
    duplas = [d for d in db.scalars(select(Dupla).where(Dupla.turma_id == tid).order_by(Dupla.numero)).all() if d.empresa]
    eventos = eventos_mes(duplas[0].empresa.caso if duplas else None, mes)
    cods = [e["codigo"] for e in eventos]
    ids = [d.id for d in duplas]
    lancs_all = db.scalars(select(Lancamento).where(Lancamento.dupla_id.in_(ids))).all() if ids else []
    msgs_all = db.scalars(select(TutorMensagem).where(TutorMensagem.dupla_id.in_(ids))).all() if ids else []
    acessos = {a.dupla_id: a for a in db.scalars(select(DuplaAcesso).where(DuplaAcesso.dupla_id.in_(ids))).all()} if ids else {}
    por_dupla_l, por_dupla_m = defaultdict(list), defaultdict(list)
    for l in lancs_all:
        por_dupla_l[l.dupla_id].append(l)
    for m in msgs_all:
        por_dupla_m[m.dupla_id].append(m)

    grupos = []
    conta_erros = defaultdict(set)  # (conta, situação) → grupos com divergência nela
    for d in duplas:
        lancs, msgs = do_mes(por_dupla_l[d.id], mes), [m for m in por_dupla_m[d.id] if (m.evento or "") in set(cods) or not m.evento]
        fech = fechamento_ativo(db, d.id, mes)
        aud = auditar(gerar_gabarito(d.empresa.valores, mes), lancs, d.empresa.caso) if lancs else None
        niveis = {e["codigo"]: e["nivel"] for e in aud["eventos"]} if aud else {c: "pendente" for c in cods}
        if fech:  # nota oficial = retrato do envio
            snap = (fech.resultado or {}).get("eventos", {})
            niveis_of = {c: (snap.get(c) or {}).get("nivel", "pendente") for c in cods}
        else:
            niveis_of = None
        if aud:
            for e in aud["eventos"]:
                for ln in e["linhas"]:
                    if ln["situacao"] != "ok":
                        conta_erros[(ln["conta"], ln["situacao"])].add(d.id)
        lancados = {l.evento for l in lancs} & set(cods)
        perguntas = [m for m in msgs if m.papel == "aluno"]
        perg_ev = Counter(m.evento for m in perguntas if m.evento)
        bloqueadas = sum(1 for m in msgs if m.origem == "filtro")
        ac = acessos.get(d.id)
        ultima = _ultima(max((l.atualizado_em or l.criado_em for l in lancs), default=None),
                         max((m.criado_em for m in perguntas), default=None), ac.ultimo_acesso if ac else None)
        autores = Counter(l.autor for l in lancs if l.autor)
        membros = [(m.discente.matricula, m.discente.nome) for m in d.membros]
        total = len([c for c in cods])
        pct_oficial = (fech.resultado or {}).get("percentual") if fech else None
        pct_previa = aud["percentual"] if aud else 0
        g = {"d": d, "membros": membros, "n_lancs": len(lancs), "lancados": len(lancados), "total": total,
             "progresso": round(100 * len(lancados) / total) if total else 0, "niveis": niveis, "niveis_oficiais": niveis_of,
             "fech": fech, "pct": pct_oficial if fech else pct_previa, "oficial": bool(fech),
             "perguntas": len(perguntas), "perg_ev": perg_ev, "bloqueadas": bloqueadas,
             "ultima": ultima, "dias": max(0, (agora - ultima).days) if ultima else None, "acessou": bool(ultima),
             "autores": autores, "alertas": [],
             "dias_ate_envio": _dias_ate_envio(lancs, fech)}
        grupos.append(g)

    # ------------------------------------------------------------------ alertas precoces
    med = median([g["lancados"] for g in grupos]) if grupos else 0
    for g in grupos:
        a = g["alertas"]
        if not g["acessou"]:
            a.append(("alto", "Sem acesso", "O grupo ainda não entrou no sistema."))
        elif g["dias"] is not None and g["dias"] >= DIAS_INATIVO and not g["fech"]:
            a.append(("alto", "Inativo", f"Sem atividade há {g['dias']} dias."))
        if not g["fech"] and med >= 6 and g["lancados"] < med / 2:
            a.append(("medio", "Abaixo da turma", f"{g['lancados']} eventos lançados; a mediana da turma é {med:g}."))
        for ev, nome in EVENTOS_CRITICOS.items():
            if g["perg_ev"].get(ev, 0) >= 3 and g["niveis"].get(ev) in ("pendente", "conta"):
                a.append(("medio", f"Travado em {ev}", f"{g['perg_ev'][ev]} perguntas ao tutor sobre {nome} e o evento "
                          f"{'ainda não foi lançado' if g['niveis'].get(ev) == 'pendente' else 'está com conta errada (prévia)'}."))
        corretos = sum(1 for c, nv in g["niveis"].items() if nv == "correto")
        acerto = round(100 * corretos / g["lancados"]) if g["lancados"] else 0
        if not g["fech"] and g["lancados"] >= 10 and acerto < 60:
            a.append(("medio", "Prévia baixa", f"Só {acerto}% dos {g['lancados']} eventos lançados conferem com o gabarito."))
        if g["bloqueadas"] >= 3:
            a.append(("baixo", "Busca respostas prontas", f"{g['bloqueadas']} respostas do tutor bloqueadas pelo filtro."))
        if len(g["membros"]) > 1 and g["n_lancs"] >= 8:
            tot = sum(g["autores"].values())
            maior = max((g["autores"].get(mat, 0) for mat, _ in g["membros"]), default=0)
            if tot and maior / tot >= 0.9:
                a.append(("baixo", "Participação desigual", f"{round(100 * maior / tot)}% dos lançamentos feitos por um só integrante."))
        peso = {"alto": 3, "medio": 2, "baixo": 1}
        g["risco"] = sum(peso[x[0]] for x in a)
    grupos_ord = sorted(grupos, key=lambda g: (-g["risco"], g["d"].numero))

    # ------------------------------------------------------------------ matriz de calor e dificuldades
    n = len(grupos)
    linhas_ev = []
    for e in eventos:
        c = e["codigo"]
        cont = Counter(g["niveis"].get(c, "pendente") for g in grupos)
        lanc = n - cont["pendente"]
        perg = sum(g["perg_ev"].get(c, 0) for g in grupos)
        erro = cont["valor"] + cont["conta"]
        linhas_ev.append({**e, "cont": cont, "lancados": lanc, "erros": erro, "perguntas": perg,
                          "pct_erro": round(100 * erro / lanc) if lanc else None,
                          "celulas": [(g["d"], g["niveis"].get(c, "pendente"), g["perg_ev"].get(c, 0)) for g in grupos]})
    temas = []
    for tema, evs in TEMAS:
        ls = [l for l in linhas_ev if l["codigo"] in evs]
        if not ls:
            continue
        lanc = sum(l["lancados"] for l in ls)
        erro = sum(l["erros"] for l in ls)
        temas.append({"tema": tema, "eventos": evs, "lancados": lanc, "erros": erro,
                      "pct_erro": round(100 * erro / lanc) if lanc else None,
                      "perguntas": sum(l["perguntas"] for l in ls),
                      "bloqueadas": sum(1 for m in msgs_all if m.origem == "filtro" and TEMA_DO_EVENTO.get(m.evento or "") == tema)})
    max_perg = max([t_["perguntas"] for t_ in temas] + [1])
    for t_ in temas:
        t_["calor_erro"] = _faixa(t_["pct_erro"])
        t_["calor_perg"] = _faixa(round(100 * t_["perguntas"] / max_perg) if t_["perguntas"] else 0)
    SIT = {"falta": "faltou", "sobra": "sobrou", "lado": "lado trocado", "valor": "valor"}
    contas = [{"conta": c, "nome": pc.CONTAS.get(c, {}).get("nome", c), "situacao": SIT[s], "grupos": k,
               "pct": round(100 * k / n) if n else 0}
              for (c, s), k in sorted(((ch, len(v)) for ch, v in conta_erros.items()), key=lambda x: -x[1])[:10]]

    # ------------------------------------------------------------------ engajamento (30 dias)
    inicio = (agora - timedelta(days=29)).date()
    dias = [inicio + timedelta(days=i) for i in range(30)]
    serie = {"lancamentos": Counter(), "perguntas": Counter()}
    for l in lancs_all:
        if l.criado_em and l.criado_em.date() >= inicio:
            serie["lancamentos"][l.criado_em.date()] += 1
    for m in msgs_all:
        if m.papel == "aluno" and m.criado_em and m.criado_em.date() >= inicio:
            serie["perguntas"][m.criado_em.date()] += 1
    ativos7 = sum(1 for g in grupos if g["dias"] is not None and g["dias"] < 7)
    engaj = {"dias": dias, "series": {k: [v.get(dd, 0) for dd in dias] for k, v in serie.items()}, "ativos7": ativos7}

    enviados = [g for g in grupos if g["fech"]]
    resumo = {
        "grupos": n, "enviados": len(enviados), "ativos7": ativos7,
        "progresso_medio": round(sum(g["progresso"] for g in grupos) / n) if n else 0,
        "media_oficial": round(sum(g["pct"] for g in enviados) / len(enviados)) if enviados else None,
        "perguntas": sum(g["perguntas"] for g in grupos), "bloqueadas": sum(g["bloqueadas"] for g in grupos),
        "alertas": sum(len(g["alertas"]) for g in grupos), "em_risco": sum(1 for g in grupos if g["risco"] >= 3),
        "tempo_medio": _media([g["dias_ate_envio"] for g in enviados]),
    }
    return {"t": t, "grupos": grupos_ord, "eventos": linhas_ev, "temas": temas, "contas": contas, "engaj": engaj,
            "resumo": resumo, "mediana": med, "mes": mes}


def _dias_ate_envio(lancs, fech) -> float | None:
    """Tempo de escrituração do mês: do primeiro lançamento ao envio do fechamento, em dias (métrica do item 4.3)."""
    if not fech or not lancs:
        return None
    inicio = min(l.criado_em for l in lancs if l.criado_em)
    return round(max(0.0, (fech.enviado_em - inicio).total_seconds() / 86400), 1)


def _media(xs) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def _faixa(pct) -> int:
    """0–4 para a escala sequencial da matriz de calor (None = sem dados)."""
    if pct is None:
        return -1
    return 0 if pct == 0 else 1 if pct < 20 else 2 if pct < 40 else 3 if pct < 60 else 4


# --------------------------------------------------------------------- notas de janeiro
def propor_notas(db: Session, tid: int, mes: str = "2026-01") -> list[dict]:
    """Nota preliminar de cada aluno: critério objetivo sobre o fechamento enviado pelo grupo
    (correto = 1, valor divergente = 0,5, conta errada ou pendente = 0) × 10 ÷ eventos do mês."""
    linhas = []
    duplas = [d for d in db.scalars(select(Dupla).where(Dupla.turma_id == tid).order_by(Dupla.numero)).all() if d.empresa]
    existentes = {(n.discente_id, n.periodo): n for n in db.scalars(select(NotaPeriodo).where(NotaPeriodo.turma_id == tid)).all()}
    for d in duplas:
        fech = fechamento_ativo(db, d.id, mes)
        if mes == "2026-01":
            total = len(eventos_janeiro(d.empresa.caso))
        else:  # fevereiro: só os eventos com correção automática no envio contam
            total = ((fech.resultado or {}).get("total") if fech else None) or len(eventos_mes(d.empresa.caso, mes))
        snap = ((fech.resultado or {}).get("eventos") or {}) if fech else {}
        niveis = {c: v.get("nivel") for c, v in snap.items()}
        sistema = nota_por_niveis(niveis, total) if fech else None
        cont = Counter(niveis.values())
        for m in sorted(d.membros, key=lambda m: m.discente.nome):
            n = existentes.get((m.discente_id, mes))
            if n is None:
                n = NotaPeriodo(turma_id=tid, dupla_id=d.id, discente_id=m.discente_id, periodo=mes, ajuste=0.0)
                db.add(n)
            if not n.homologada:  # enquanto não homologada, acompanha o fechamento (inclusive reaberto/reenviado)
                n.nota_sistema, n.dupla_id = sistema, d.id
            linhas.append({"d": d, "m": m, "n": n, "fech": fech, "cont": cont, "total": total})
    db.commit()
    return linhas


def resumo_gestao(db: Session, turmas: list[Turma]) -> list[dict]:
    """Linha por turma para o Painel de Gestão (sem calcular prévias: rápido para muitas turmas)."""
    from .acesso import status_turma, Usuario
    out = []
    for t in turmas:
        duplas = [d for d in db.scalars(select(Dupla).where(Dupla.turma_id == t.id)).all() if d.empresa]
        ids = [d.id for d in duplas]
        alunos = [m.discente_id for d in duplas for m in d.membros]
        contas = db.scalar(select(func.count(Usuario.id)).where(Usuario.discente_id.in_(alunos))) if alunos else 0
        n_l = len(db.execute(select(Lancamento.dupla_id, Lancamento.evento).where(Lancamento.dupla_id.in_(ids)).distinct()).all()) if ids else 0
        fechs = [f for f in (fechamento_ativo(db, i) for i in ids) if f]
        fechs_fev = [f for f in (fechamento_ativo(db, i, "2026-02") for i in ids) if f]
        pcts = [(f.resultado or {}).get("percentual", 0) for f in fechs]
        tempos = []
        for f in fechs:
            ini = db.scalar(select(func.min(Lancamento.criado_em)).where(Lancamento.dupla_id == f.dupla_id))
            if ini:
                tempos.append(max(0.0, (f.enviado_em - ini).total_seconds() / 86400))
        perg = db.scalar(select(func.count(TutorMensagem.id)).where(TutorMensagem.dupla_id.in_(ids), TutorMensagem.papel == "aluno")) if ids else 0
        ult_l = db.scalar(select(func.max(Lancamento.criado_em)).where(Lancamento.dupla_id.in_(ids))) if ids else None
        ult_a = db.scalar(select(func.max(DuplaAcesso.ultimo_acesso)).where(DuplaAcesso.dupla_id.in_(ids))) if ids else None
        homolog = db.scalar(select(func.count(NotaPeriodo.id)).where(NotaPeriodo.turma_id == t.id, NotaPeriodo.homologada.is_(True)))
        n_ev = len(eventos_ate(duplas[0].empresa.caso, "2026-02")) if duplas else 92
        out.append({"t": t, "status": status_turma(db, t.id), "matriculados": len(t.matriculas), "grupos": len(duplas),
                    "alunos": len(alunos), "contas": contas or 0, "adesao": round(100 * (contas or 0) / len(alunos)) if alunos else 0,
                    "progresso": round(100 * (n_l or 0) / (n_ev * len(duplas))) if duplas else 0,
                    "enviados": len(fechs), "enviados_fev": len(fechs_fev), "media": round(sum(pcts) / len(pcts)) if pcts else None,
                    "perguntas": perg or 0, "ultima": _ultima(ult_l, ult_a), "homologadas": homolog or 0,
                    "tempo_medio": _media(tempos)})
    return out
