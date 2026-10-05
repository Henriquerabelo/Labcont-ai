"""Área da dupla (aluno): acesso por código da dupla + matrícula, documentos, escrituração e auditoria.

Fica fora da senha geral do site (prefixo /aluno). A sessão é um cookie assinado (HMAC) com a dupla e a
matrícula. A dupla só vê os próprios dados: nunca o gabarito, nem as outras duplas.
"""
from __future__ import annotations

import hmac
import re
from datetime import date, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import plano_contas as pc
from ..auditoria import NIVEIS, auditar, balancete_aluno, eventos_janeiro, resumo_resultado
from ..caso_servico import num
from ..db import get_db
from ..documentos import gerar_documentos
from ..gabarito import Gabarito, gerar_gabarito, r2
from ..main import render, voltar
from ..models_dupla import Dupla, DuplaMembro
from .. import acesso
from ..acesso import Usuario, UsuarioPerfil
from ..models_escrita import DuplaAcesso, FechamentoMensal, Lancamento, Partida, TutorMensagem, fechamento_ativo
from .. import normas as normas_base
from .. import tutor as tutor_ia
from .documentos import TIPOS

router = APIRouter(prefix="/aluno")


def _dupla_do_aluno(db: Session, discente_id: int) -> Dupla | None:
    duplas = db.scalars(select(Dupla).join(DuplaMembro, DuplaMembro.dupla_id == Dupla.id)
                        .where(DuplaMembro.discente_id == discente_id).order_by(Dupla.id.desc())).all()
    return next((d for d in duplas if d.empresa), duplas[0] if duplas else None)


def _sessao(request: Request, db: Session) -> tuple[Dupla | None, str | None]:
    """Aluno logado (matrícula + senha) ou equipe visualizando um grupo (somente leitura, mat = None)."""
    c = request.state.usuario
    if c is None:
        return None, None
    if c.equipe:
        bruto = request.cookies.get(acesso.COOKIE_VER, "")
        did, _, sig = bruto.partition(".")
        if did.isdigit() and hmac.compare_digest(sig, acesso.assinar(f"ver.{did}.{c.id}")):
            d = db.get(Dupla, int(did))
            if d and c.ve_turma(d.turma_id):
                return d, None
        return None, None
    if "aluno" in c.perfis and c.discente_id:
        d = _dupla_do_aluno(db, c.discente_id)
        if d:
            mat = next((m.discente.matricula for m in d.membros if m.discente_id == c.discente_id), None)
            return d, mat
    return None, None


def _ctx(d: Dupla, mat: str | None, **kw) -> dict:
    nome = next((m.discente.nome for m in d.membros if m.discente.matricula == mat), "")
    return {"d": d, "aluno_nome": nome, "area_aluno": True, "visualizacao": mat is None, **kw}


# ------------------------------------------------------------------ acesso
@router.get("")
def inicio(request: Request, db: Session = Depends(get_db)):
    d, mat = _sessao(request, db)
    if not d:
        return render(request, "aluno/entrar.html", area_aluno=True)
    if not d.empresa:
        return render(request, "aluno/entrar.html", area_aluno=True, erro="A empresa da sua dupla ainda não foi gerada pelo professor.")
    lancs = _lancs(db, d)
    fech = fechamento_ativo(db, d.id)
    aud = auditar(gerar_gabarito(d.empresa.valores), lancs, d.empresa.caso)
    lancados = {l.evento for l in lancs}
    if not fech:  # antes do envio: só a situação de registro, sem correção
        for e in aud["eventos"]:
            e["nivel"] = "lancado" if e["codigo"] in lancados else "pendente"
    else:  # depois do envio: o resultado registrado no fechamento
        snap = (fech.resultado or {}).get("eventos", {})
        for e in aud["eventos"]:
            r = snap.get(e["codigo"], {"nivel": "pendente", "dica": ""})
            e["nivel"], e["dica"] = r["nivel"], r["dica"]
        aud["percentual"] = (fech.resultado or {}).get("percentual", 0)
        aud["contagem"] = (fech.resultado or {}).get("contagem", {})
    pend = [e for e in aud["eventos"] if e["codigo"] not in lancados]
    nota = None
    c = request.state.usuario
    if mat and c and c.discente_id:
        from ..analytics import NotaPeriodo
        nota = db.scalar(select(NotaPeriodo).where(NotaPeriodo.discente_id == c.discente_id, NotaPeriodo.periodo == "2026-01",
                                                   NotaPeriodo.homologada.is_(True)))
    from .. import consistencia
    datas = {e["codigo"]: e["data"] for e in eventos_janeiro(d.empresa.caso)}
    avisos = consistencia.verificar(_saldos_ini(d), lancs, datas)
    return render(request, "aluno/painel.html", **_ctx(d, mat, aud=aud, nota=nota, avisos=avisos,
                  avisos_cont=consistencia.contagem(avisos), niveis={**NIVEIS, "lancado": "Lançado"},
                  n_lancs=len(lancs), fech=fech, pendentes=pend, lancados=len(lancados & {e["codigo"] for e in aud["eventos"]})))


@router.post("/fechamento")
async def enviar_fechamento(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, alterar=True)
    if fora:
        return fora
    if fechamento_ativo(db, d.id):
        return voltar("/aluno", erro="O fechamento de janeiro já foi enviado.")
    form = await request.form()
    lancs = _lancs(db, d)
    if not lancs:
        return voltar("/aluno", erro="Não há lançamentos para enviar.")
    lancados = {l.evento for l in lancs}
    pend = [e["codigo"] for e in eventos_janeiro(d.empresa.caso) if e["codigo"] not in lancados]
    if pend and form.get("confirmo") != "1":
        return voltar("/aluno#fechamento", erro=f"Há {len(pend)} evento(s) sem lançamento. Marque a confirmação para enviar assim mesmo.")
    aud = auditar(gerar_gabarito(d.empresa.valores), lancs, d.empresa.caso)
    db.add(FechamentoMensal(dupla_id=d.id, mes="2026-01", enviado_por=mat, resultado=resumo_resultado(aud)))
    db.commit()
    return voltar("/aluno", "Fechamento de janeiro enviado. Veja abaixo a correção de cada evento.")


@router.post("/entrar")
async def entrar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    mat = re.sub(r"\D", "", form.get("matricula") or "")
    chave = f"aluno:{mat}"
    if acesso.bloqueado(chave):
        return render(request, "aluno/entrar.html", area_aluno=True, matricula=mat, erro="Muitas tentativas. Aguarde 5 minutos.")
    u = db.scalar(select(Usuario).where(Usuario.login == mat)) if mat else None
    if not u or not u.ativo or "aluno" not in u.nomes_perfis or not acesso.conferir(form.get("senha") or "", u.senha_hash):
        acesso.falhou(chave)
        return render(request, "aluno/entrar.html", area_aluno=True, matricula=mat,
                      erro="Matrícula ou senha não conferem. Se é o seu primeiro acesso, crie a sua senha abaixo.")
    acesso.limpar_falhas(chave)
    return _logar(request, db, u)


def _logar(request: Request, db: Session, u: Usuario):
    u.ultimo_acesso = datetime.now()
    d = _dupla_do_aluno(db, u.discente_id)
    if d:
        a = db.scalar(select(DuplaAcesso).where(DuplaAcesso.dupla_id == d.id))
        if a:
            a.ultimo_acesso = datetime.now()
    db.commit()
    acesso.registrar(db, acesso.montar_ctx(db, u), "/aluno/entrar")
    r = voltar("/aluno")
    r.set_cookie(acesso.COOKIE, acesso.cookie_sessao(u), httponly=True, samesite="lax", secure=acesso.https(request),
                 max_age=acesso.DURACAO["aluno"])
    r.delete_cookie(acesso.COOKIE_VER)
    return r


@router.post("/primeiro-acesso")
async def primeiro_acesso(request: Request, db: Session = Depends(get_db)):
    """Cria a senha do aluno: matrícula + código do grupo (entregue pelo professor) + nova senha."""
    form = await request.form()
    codigo = re.sub(r"[^A-Z0-9]", "", (form.get("codigo") or "").upper())
    mat = re.sub(r"\D", "", form.get("matricula_pa") or "")
    ctx = {"area_aluno": True, "codigo": codigo, "matricula_pa": mat, "aba": "primeiro"}
    chave = f"pa:{mat}"
    if acesso.bloqueado(chave):
        return render(request, "aluno/entrar.html", erro="Muitas tentativas. Aguarde 5 minutos.", **ctx)
    ac = db.scalar(select(DuplaAcesso).where(DuplaAcesso.codigo == codigo)) if codigo else None
    membro = next((m for m in ac.dupla.membros if m.discente.matricula == mat), None) if ac else None
    if not membro:
        acesso.falhou(chave)
        return render(request, "aluno/entrar.html", erro="Código do grupo ou matrícula não conferem.", **ctx)
    if db.scalar(select(Usuario).where(Usuario.login == mat)):
        return render(request, "aluno/entrar.html", erro="Esta matrícula já tem senha. Entre com ela ou peça ao professor para apagá-la.", **ctx)
    nova = form.get("nova") or ""
    erro = acesso.validar_senha(nova) or (None if nova == form.get("nova2") else "As duas senhas não são iguais.")
    if not erro and form.get("ciente") != "1":
        erro = "Para criar a senha, confirme que leu o aviso de privacidade."
    if erro:
        return render(request, "aluno/entrar.html", erro=erro, **ctx)
    u = Usuario(login=mat, nome=membro.discente.nome, senha_hash=acesso.gerar_hash(nova), discente_id=membro.discente_id)
    u.perfis.append(UsuarioPerfil(perfil="aluno"))
    db.add(u)
    db.commit()
    acesso.limpar_falhas(chave)
    from ..main import PRIVACIDADE_VERSAO
    acesso.registrar(db, acesso.montar_ctx(db, u), "/aluno/primeiro-acesso",
                     detalhe=f"Ciente do aviso de privacidade, versão {PRIVACIDADE_VERSAO}.")
    return _logar(request, db, u)


@router.get("/sair")
def sair(request: Request):
    c = request.state.usuario
    if c and c.equipe:  # equipe saindo da visualização do grupo
        r = voltar("/duplas", "Você saiu da visualização da área do aluno.")
        r.delete_cookie(acesso.COOKIE_VER)
        return r
    r = voltar("/aluno", "Você saiu da área do grupo.")
    r.delete_cookie(acesso.COOKIE)
    return r


@router.get("/ver/{did}")
def ver_como_aluno(request: Request, did: int):
    """Equipe abre a área do aluno de um grupo em modo somente leitura (a regra de acesso já conferiu a turma)."""
    c = request.state.usuario
    r = voltar("/aluno")
    r.set_cookie(acesso.COOKIE_VER, f"{did}.{acesso.assinar(f'ver.{did}.{c.id}')}", httponly=True, samesite="lax",
                 secure=acesso.https(request), max_age=60 * 60 * 4)
    return r


def _exigir(request: Request, db: Session, escrita: bool = False, alterar: bool = False):
    """escrita: lançamentos (bloqueia após o fechamento); alterar: qualquer gravação (bloqueia visualização e turma encerrada)."""
    d, mat = _sessao(request, db)
    if not d or not d.empresa:
        return None, None, voltar("/aluno")
    if (escrita or alterar) and mat is None:
        return None, None, voltar("/aluno", erro="Visualização da equipe: somente leitura.")
    if (escrita or alterar) and acesso.turma_encerrada(db, d.turma_id):
        return None, None, voltar("/aluno", erro="A turma foi encerrada: a área do grupo agora é somente leitura.")
    if escrita and fechamento_ativo(db, d.id):
        return None, None, voltar("/aluno", erro="Janeiro já foi enviado: a escrituração está bloqueada. Peça ao professor para reabrir, se necessário.")
    return d, mat, None


def _lancs(db: Session, d: Dupla) -> list[Lancamento]:
    return db.scalars(select(Lancamento).where(Lancamento.dupla_id == d.id).order_by(Lancamento.data, Lancamento.evento, Lancamento.id)).all()


# ------------------------------------------------------------------ documentos e orientação
@router.get("/documentos")
def documentos(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    return render(request, "aluno/documentos.html", **_ctx(d, mat, docs=gerar_documentos(d.empresa.valores), tipos=TIPOS))


@router.get("/documentos/{doc_id}")
def documento(request: Request, doc_id: str, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    docs = gerar_documentos(d.empresa.valores)
    i = next((k for k, x in enumerate(docs) if x["id"] == doc_id), None)
    if i is None:
        return voltar("/aluno/documentos", erro="Documento não encontrado.")
    return render(request, "aluno/documento.html", **_ctx(d, mat, doc=docs[i], tipos=TIPOS,
                  anterior=docs[i - 1]["id"] if i > 0 else None, proximo=docs[i + 1]["id"] if i + 1 < len(docs) else None))


@router.get("/orientacao.docx")
def orientacao(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    from urllib.parse import quote
    from .duplas import DOCX, _docx, _nome_arquivo
    return Response(_docx(d), media_type=DOCX,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(_nome_arquivo(d))}"})


# ------------------------------------------------------------------ escrituração
def _conta_de(texto: str) -> str | None:
    t = (texto or "").strip()
    cod = t.split(" ")[0].strip()
    if cod in pc.CONTAS:
        return cod
    alvo = t.lower()
    achadas = [c for c, i in pc.CONTAS.items() if i["nome"].lower() == alvo]
    return achadas[0] if len(achadas) == 1 else None


def _ler_form(form) -> tuple[dict, list[str]]:
    erros = []
    ev = (form.get("evento") or "").strip().upper()
    try:
        dt = date.fromisoformat(form.get("data") or "")
    except ValueError:
        dt = None
        erros.append("Informe a data do lançamento.")
    hist = (form.get("historico") or "").strip()
    if not ev:
        erros.append("Escolha o evento.")
    if not hist:
        erros.append("Escreva o histórico.")
    partidas = []
    contas, nats, vals = form.getlist("conta"), form.getlist("natureza"), form.getlist("valor")
    for i, (c, n, v) in enumerate(zip(contas, nats, vals), 1):
        if not (c or "").strip() and not (v or "").strip():
            continue
        cod = _conta_de(c)
        val = num(v)
        if not cod:
            erros.append(f"Linha {i}: conta “{c}” não existe no plano de contas.")
        if val is None or val <= 0:
            erros.append(f"Linha {i}: valor inválido.")
        if n not in ("D", "C"):
            erros.append(f"Linha {i}: indique débito ou crédito.")
        partidas.append({"conta": cod or c, "natureza": n, "valor": r2(val or 0), "texto": c})
    td = r2(sum(p["valor"] for p in partidas if p["natureza"] == "D"))
    tc = r2(sum(p["valor"] for p in partidas if p["natureza"] == "C"))
    if not any(p["natureza"] == "D" for p in partidas) or not any(p["natureza"] == "C" for p in partidas):
        erros.append("O lançamento precisa de pelo menos um débito e um crédito.")
    elif td != tc:
        erros.append(f"Débitos ({td:,.2f}) diferentes dos créditos ({tc:,.2f}).".replace(",", "X").replace(".", ",").replace("X", "."))
    return {"evento": ev, "data": dt, "historico": hist, "partidas": partidas}, erros


def _form_ctx(d, mat, dados=None, lanc_id=None, erro=None):
    eventos = eventos_janeiro(d.empresa.caso)
    contas = [f"{c} {i['nome']}" for c, i in pc.CONTAS.items()]
    return _ctx(d, mat, eventos=eventos, contas=contas, dados=dados or {}, lanc_id=lanc_id, erro=erro)


@router.get("/lancar")
def lancar_form(request: Request, evento: str = "", db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, escrita=True)
    if fora:
        return fora
    ev = next((e for e in eventos_janeiro(d.empresa.caso) if e["codigo"] == evento.upper()), None)
    dados = {"evento": ev["codigo"], "data": ev["data"].isoformat(), "historico": "", "partidas": []} if ev else {}
    return render(request, "aluno/lancar.html", **_form_ctx(d, mat, dados))


@router.post("/lancar")
async def lancar(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, escrita=True)
    if fora:
        return fora
    dados, erros = _ler_form(await request.form())
    if erros:
        dados["data"] = dados["data"].isoformat() if dados["data"] else ""
        return render(request, "aluno/lancar.html", **_form_ctx(d, mat, dados, erro=" ".join(erros)))
    l = Lancamento(dupla_id=d.id, evento=dados["evento"], data=dados["data"], historico=dados["historico"], autor=mat)
    l.partidas = [Partida(ordem=i, conta=p["conta"], natureza=p["natureza"], valor=p["valor"]) for i, p in enumerate(dados["partidas"])]
    db.add(l)
    db.commit()
    return voltar(*_apos_gravar(db, d, l, "registrado"))


def _apos_gravar(db: Session, d: Dupla, l: Lancamento, acao: str) -> tuple[str, str]:
    """Mensagem após gravar, com os avisos estruturais do evento (sem comparar com o gabarito)."""
    from .. import consistencia
    datas = {e["codigo"]: e["data"] for e in eventos_janeiro(d.empresa.caso)}
    avs = [a for a in consistencia.verificar(_saldos_ini(d), _lancs(db, d), datas)
           if a.get("lancamento_id") == l.id or a["nivel"] == "erro"]
    msg = f"Lançamento do evento {l.evento} {acao}."
    if avs:
        msg += f" Conferência imediata: {len(avs)} ponto(s) para revisar — veja no painel."
        return "/aluno#avisos", msg
    return f"/aluno#ev-{l.evento}", msg


@router.get("/lancamentos/{lid}/editar")
def editar_form(request: Request, lid: int, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, escrita=True)
    if fora:
        return fora
    l = db.get(Lancamento, lid)
    if not l or l.dupla_id != d.id:
        return voltar("/aluno/diario", erro="Lançamento não encontrado.")
    dados = {"evento": l.evento, "data": l.data.isoformat(), "historico": l.historico,
             "partidas": [{"texto": f"{p.conta} {pc.CONTAS.get(p.conta, {}).get('nome', '')}", "natureza": p.natureza, "valor": p.valor}
                          for p in l.partidas]}
    return render(request, "aluno/lancar.html", **_form_ctx(d, mat, dados, lanc_id=lid))


@router.post("/lancamentos/{lid}/editar")
async def editar(request: Request, lid: int, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, escrita=True)
    if fora:
        return fora
    l = db.get(Lancamento, lid)
    if not l or l.dupla_id != d.id:
        return voltar("/aluno/diario", erro="Lançamento não encontrado.")
    dados, erros = _ler_form(await request.form())
    if erros:
        dados["data"] = dados["data"].isoformat() if dados["data"] else ""
        return render(request, "aluno/lancar.html", **_form_ctx(d, mat, dados, lanc_id=lid, erro=" ".join(erros)))
    l.evento, l.data, l.historico, l.autor = dados["evento"], dados["data"], dados["historico"], mat
    l.partidas = [Partida(ordem=i, conta=p["conta"], natureza=p["natureza"], valor=p["valor"]) for i, p in enumerate(dados["partidas"])]
    db.commit()
    return voltar(*_apos_gravar(db, d, l, "atualizado"))


@router.post("/lancamentos/{lid}/excluir")
def excluir(request: Request, lid: int, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, escrita=True)
    if fora:
        return fora
    l = db.get(Lancamento, lid)
    if l and l.dupla_id == d.id:
        db.delete(l)
        db.commit()
    return voltar("/aluno/diario", "Lançamento excluído.")


# ------------------------------------------------------------------ livros
@router.get("/diario")
def diario(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    return render(request, "aluno/diario.html", **_ctx(d, mat, lancs=_lancs(db, d), contas=pc.CONTAS, fech=fechamento_ativo(db, d.id)))


def _saldos_ini(d: Dupla) -> dict:
    return Gabarito(d.empresa.valores).L.ini


@router.get("/balancete")
def balancete(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    bal = balancete_aluno(_saldos_ini(d), _lancs(db, d))
    tot_d = r2(sum(x["final"] for x in bal if x["final"] > 0))
    tot_c = r2(-sum(x["final"] for x in bal if x["final"] < 0))
    return render(request, "aluno/balancete.html", **_ctx(d, mat, bal=bal, tot_d=tot_d, tot_c=tot_c))


@router.get("/demonstracoes")
def demonstracoes_aluno(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    from .. import demonstracoes as dm
    parts = [(p.conta, p.natureza, p.valor) for l in _lancs(db, d) for p in l.partidas]
    r = dm.montar(dm.saldos_finais(_saldos_ini(d), parts))
    return render(request, "aluno/demonstracoes.html", **_ctx(d, mat, r=r))


@router.get("/razao")
def razao(request: Request, conta: str = "", db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    cod = _conta_de(conta) or pc.BANCO
    saldo = _saldos_ini(d).get(cod, 0.0)
    linhas = [{"data": None, "historico": "Saldo inicial em 31/12/2025", "d": None, "c": None, "saldo": r2(saldo)}]
    for l in _lancs(db, d):
        for p in l.partidas:
            if p.conta == cod:
                saldo += p.valor if p.natureza == "D" else -p.valor
                linhas.append({"data": l.data, "evento": l.evento, "historico": l.historico, "lid": l.id,
                               "d": p.valor if p.natureza == "D" else None, "c": p.valor if p.natureza == "C" else None,
                               "saldo": r2(saldo)})
    contas = [f"{c} {i['nome']}" for c, i in pc.CONTAS.items()]
    return render(request, "aluno/razao.html", **_ctx(d, mat, conta=cod, nome=pc.CONTAS[cod]["nome"], linhas=linhas, contas=contas))


# ------------------------------------------------------------------ tutor
def _historico(db: Session, d: Dupla, evento: str | None) -> list[TutorMensagem]:
    q = select(TutorMensagem).where(TutorMensagem.dupla_id == d.id)
    q = q.where(TutorMensagem.evento == evento) if evento else q.where(TutorMensagem.evento.is_(None))
    return db.scalars(q.order_by(TutorMensagem.id)).all()


@router.get("/tutor")
def tutor_tela(request: Request, evento: str = "", db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    eventos = eventos_janeiro(d.empresa.caso)
    ev = next((e for e in eventos if e["codigo"] == evento.upper()), None)
    msgs = _historico(db, d, ev["codigo"] if ev else None)
    usados = {m.evento for m in db.scalars(select(TutorMensagem).where(TutorMensagem.dupla_id == d.id)).all() if m.evento}
    return render(request, "aluno/tutor.html", **_ctx(d, mat, eventos=eventos, ev=ev, msgs=msgs, usados=usados,
                  fech=fechamento_ativo(db, d.id)))


@router.post("/tutor")
async def tutor_perguntar(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db, alterar=True)
    if fora:
        return fora
    form = await request.form()
    pergunta = (form.get("pergunta") or "").strip()[:1500]
    eventos = eventos_janeiro(d.empresa.caso)
    ev = next((e for e in eventos if e["codigo"] == (form.get("evento") or "").upper()), None)
    volta = f"/aluno/tutor?evento={ev['codigo']}#fim" if ev else "/aluno/tutor#fim"
    if not pergunta:
        return voltar(volta, erro="Escreva a pergunta.")
    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    n_hoje = sum(1 for m in db.scalars(select(TutorMensagem).where(TutorMensagem.dupla_id == d.id, TutorMensagem.papel == "aluno",
                                                                   TutorMensagem.criado_em >= hoje)).all())
    if n_hoje >= tutor_ia.LIMITE_DIARIO:
        return voltar(volta, erro=f"Limite de {tutor_ia.LIMITE_DIARIO} perguntas por dia atingido. Volte amanhã ou fale com o professor.")
    fech = fechamento_ativo(db, d.id)
    regras, correcao = [], None
    if ev:
        g = gerar_gabarito(d.empresa.valores)  # usado só para saber quais regras do caso valem para o evento
        val = ((d.empresa.caso.dados or {}).get("premissas_validacao") or {}) if d.empresa.caso else {}
        from ..gabarito import PREMISSAS
        regras = [PREMISSAS[k] for k in g["premissas_evento"].get(ev["codigo"], [])
                  if (val.get(k) or {}).get("status") == "VALIDADA" and k in PREMISSAS]
        if fech:
            correcao = ((fech.resultado or {}).get("eventos") or {}).get(ev["codigo"])
    achadas = [n for n, _ in normas_base.buscar(normas_base.todas(db), pergunta, ev["codigo"] if ev else None,
                                                 apoio=ev["descricao"] if ev else "")]
    ctx = tutor_ia.contexto(ev, gerar_documentos(d.empresa.valores), _lancs(db, d), regras, correcao,
                            com_valores=bool(fech), normas=achadas)
    hist = [(m.papel, m.texto) for m in _historico(db, d, ev["codigo"] if ev else None)]
    resposta, origem = await tutor_ia.responder(pergunta, ctx, hist, bool(fech), ev["codigo"] if ev else None)
    resposta += tutor_ia.fontes(achadas)
    cod = ev["codigo"] if ev else None
    agora = datetime.now()  # mesma referência de hora usada no limite diário
    db.add(TutorMensagem(dupla_id=d.id, evento=cod, papel="aluno", texto=pergunta, matricula=mat, criado_em=agora))
    db.add(TutorMensagem(dupla_id=d.id, evento=cod, papel="tutor", texto=resposta, origem=origem, criado_em=agora))
    db.commit()
    return voltar(volta)


# ------------------------------------------------------------------ normas (consulta)
@router.get("/normas")
def normas_consulta(request: Request, q: str = "", evento: str = "", db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora:
        return fora
    todas = [n for n in normas_base.todas(db) if n.ativa]
    resultado = normas_base.buscar(todas, q, evento or None, k=6) if (q or evento) else None
    return render(request, "aluno/normas.html", **_ctx(d, mat, normas=todas, q=q, evento=evento.upper(), resultado=resultado))


# ------------------------------------------------------------------ senha do aluno
@router.get("/senha")
def senha_tela(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora or mat is None:
        return fora or voltar("/aluno")
    return render(request, "aluno/senha.html", **_ctx(d, mat, menu="senha"))


@router.post("/senha")
async def senha_trocar(request: Request, db: Session = Depends(get_db)):
    d, mat, fora = _exigir(request, db)
    if fora or mat is None:
        return fora or voltar("/aluno")
    form = await request.form()
    u = db.get(Usuario, request.state.usuario.id)
    erro = None if acesso.conferir(form.get("atual") or "", u.senha_hash) else "A senha atual não confere."
    nova = form.get("nova") or ""
    erro = erro or acesso.validar_senha(nova) or (None if nova == form.get("nova2") else "As duas senhas não são iguais.")
    if erro:
        return render(request, "aluno/senha.html", **_ctx(d, mat, menu="senha", erro=erro))
    u.senha_hash = acesso.gerar_hash(nova)
    db.commit()
    r = voltar("/aluno", "Senha alterada.")
    r.set_cookie(acesso.COOKIE, acesso.cookie_sessao(u), httponly=True, samesite="lax", secure=acesso.https(request),
                 max_age=acesso.DURACAO["aluno"])
    return r
