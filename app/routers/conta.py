"""Etapa 7 · Entrada da equipe, troca de senha, usuários e perfis, histórico e situação da turma."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import acesso
from ..acesso import EQUIPE, PERFIS, Acao, TurmaStatus, Usuario, UsuarioPerfil
from ..db import get_db
from ..main import render, voltar
from ..models import Docente, Turma

router = APIRouter()


def _volta_segura(v: str | None) -> str:
    return v if v and v.startswith("/") and not v.startswith("//") else "/"


# ------------------------------------------------------------------ entrar / sair
@router.get("/entrar")
def entrar_tela(request: Request, volta: str = ""):
    return render(request, "conta/entrar.html", volta=_volta_segura(volta))


@router.post("/entrar")
async def entrar(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    login = (form.get("login") or "").strip().lower()
    volta = _volta_segura(form.get("volta"))
    if acesso.bloqueado(login):
        return render(request, "conta/entrar.html", volta=volta, login=login,
                      erro="Muitas tentativas. Aguarde 5 minutos e tente de novo.")
    u = db.scalar(select(Usuario).where(Usuario.login == login))
    if not u or not u.ativo or not acesso.conferir(form.get("senha") or "", u.senha_hash) or not (u.nomes_perfis & set(EQUIPE)):
        acesso.falhou(login)
        acesso.registrar(db, None, "/entrar", "Tentativa de entrada recusada", login=login)
        return render(request, "conta/entrar.html", volta=volta, login=login, erro="Usuário ou senha não conferem.")
    acesso.limpar_falhas(login)
    u.ultimo_acesso = datetime.now()
    db.commit()
    acesso.registrar(db, acesso.montar_ctx(db, u), "/entrar")
    r = voltar("/conta/senha" if u.trocar_senha else volta)
    r.set_cookie(acesso.COOKIE, acesso.cookie_sessao(u), httponly=True, samesite="lax", secure=acesso.https(request),
                 max_age=acesso.DURACAO["equipe"])
    r.delete_cookie(acesso.COOKIE_VER)
    return r


@router.get("/sair")
def sair(request: Request):
    c = request.state.usuario
    r = voltar("/aluno" if c and not c.equipe else "/entrar", "Você saiu do sistema.")
    r.delete_cookie(acesso.COOKIE)
    r.delete_cookie(acesso.COOKIE_VER)
    return r


@router.get("/conta/senha")
def senha_tela(request: Request):
    return render(request, "conta/senha.html")


@router.post("/conta/senha")
async def senha_trocar(request: Request, db: Session = Depends(get_db)):
    c = request.state.usuario
    if c.dev:
        return voltar("/", erro="Modo local sem usuários: não há senha para trocar.")
    form = await request.form()
    u = db.get(Usuario, c.id)
    if not acesso.conferir(form.get("atual") or "", u.senha_hash):
        return render(request, "conta/senha.html", erro="A senha atual não confere.")
    nova = form.get("nova") or ""
    erro = acesso.validar_senha(nova) or (None if nova == form.get("nova2") else "As duas senhas novas não são iguais.")
    if erro:
        return render(request, "conta/senha.html", erro=erro)
    u.senha_hash = acesso.gerar_hash(nova)
    u.trocar_senha = False
    db.commit()
    r = voltar("/", "Senha alterada.")
    r.set_cookie(acesso.COOKIE, acesso.cookie_sessao(u), httponly=True, samesite="lax", secure=acesso.https(request),
                 max_age=acesso.DURACAO["equipe"])
    return r


# ------------------------------------------------------------------ usuários
def _concedíveis(c) -> list[str]:
    """Perfis que este usuário pode atribuir: admin todos; coordenador só professor, monitor e visitante."""
    return list(EQUIPE) if c.admin else ["professor", "monitor", "visitante"]


def _pode_editar(c, u: Usuario) -> bool:
    return c.admin or not (u.nomes_perfis & {"admin", "coordenador"})


@router.get("/usuarios")
def usuarios(request: Request, q: str = "", perfil: str = "", db: Session = Depends(get_db)):
    qs = select(Usuario).order_by(Usuario.nome)
    if q:
        qs = qs.where(or_(Usuario.nome.ilike(f"%{q}%"), Usuario.login.ilike(f"%{q}%")))
    lista = db.scalars(qs).all()
    if perfil:
        lista = [u for u in lista if perfil in u.nomes_perfis]
    elif not q:
        lista = [u for u in lista if u.nomes_perfis & set(EQUIPE)]  # alunos só com filtro/busca
    n_alunos = db.scalar(select(func.count(UsuarioPerfil.id)).where(UsuarioPerfil.perfil == "aluno"))
    return render(request, "conta/usuarios.html", lista=lista, q=q, perfil=perfil, perfis=PERFIS, n_alunos=n_alunos,
                  menu="usuarios")


def _form_ctx(db: Session, c, u: Usuario | None, **kw) -> dict:
    return {"u": u, "perfis": PERFIS, "concediveis": _concedíveis(c), "menu": "usuarios",
            "docentes": db.scalars(select(Docente).order_by(Docente.nome)).all(),
            "turmas": db.scalars(select(Turma).order_by(Turma.periodo.desc(), Turma.codigo)).all(), **kw}


@router.get("/usuarios/novo")
def usuario_novo(request: Request, db: Session = Depends(get_db)):
    return render(request, "conta/usuario.html", **_form_ctx(db, request.state.usuario, None))


async def _aplicar(request: Request, db: Session, u: Usuario) -> str | None:
    c = request.state.usuario
    form = await request.form()
    u.nome = (form.get("nome") or "").strip()
    u.login = (form.get("login") or "").strip().lower()
    if not u.nome or not u.login:
        return "Informe nome e login (e-mail)."
    outro = db.scalar(select(Usuario).where(Usuario.login == u.login, Usuario.id != (u.id or 0)))
    if outro:
        return "Já existe um usuário com esse login."
    escolhidos = [p for p in form.getlist("perfil") if p in _concedíveis(c)]
    if not escolhidos:
        return "Marque pelo menos um perfil."
    u.docente_id = int(form["docente_id"]) if (form.get("docente_id") or "").isdigit() else None
    if "professor" in escolhidos and not u.docente_id:
        return "Para o perfil professor, escolha o docente correspondente (as turmas vêm do vínculo docente ↔ turma)."
    turmas_mon = [int(t) for t in form.getlist("turma_monitor") if t.isdigit()]
    if "monitor" in escolhidos and not turmas_mon:
        return "Para o perfil monitor, marque as turmas que ele acompanha."
    mantidos = [p for p in u.perfis if p.perfil not in _concedíveis(c) and p.perfil != "aluno"]  # perfis que o coordenador não mexe
    novos = [UsuarioPerfil(perfil=p) for p in escolhidos if p != "monitor"]
    novos += [UsuarioPerfil(perfil="monitor", turma_id=t) for t in turmas_mon] if "monitor" in escolhidos else []
    u.perfis = mantidos + [p for p in u.perfis if p.perfil == "aluno"] + novos
    u.ativo = form.get("ativo") == "on" if u.id else True
    return None


@router.post("/usuarios/novo")
async def usuario_criar(request: Request, db: Session = Depends(get_db)):
    c = request.state.usuario
    u = Usuario(nome="", login="", senha_hash="")
    erro = await _aplicar(request, db, u)
    if erro:
        db.rollback()
        return render(request, "conta/usuario.html", **_form_ctx(db, c, u, erro=erro))
    senha = acesso.senha_provisoria()
    u.senha_hash = acesso.gerar_hash(senha)
    u.trocar_senha = True
    db.add(u)
    db.commit()
    return render(request, "conta/senha_gerada.html", u=u, senha=senha, novo=True, menu="usuarios")


@router.get("/usuarios/{id}")
def usuario_editar(request: Request, id: int, db: Session = Depends(get_db)):
    c = request.state.usuario
    u = db.get(Usuario, id)
    if not u or not _pode_editar(c, u):
        return voltar("/usuarios", erro="Usuário não encontrado ou fora do seu perfil.")
    return render(request, "conta/usuario.html", **_form_ctx(db, c, u))


@router.post("/usuarios/{id}")
async def usuario_salvar(request: Request, id: int, db: Session = Depends(get_db)):
    c = request.state.usuario
    u = db.get(Usuario, id)
    if not u or not _pode_editar(c, u):
        return voltar("/usuarios", erro="Usuário não encontrado ou fora do seu perfil.")
    erro = await _aplicar(request, db, u)
    if not erro and u.id == c.id and "admin" not in u.nomes_perfis and c.admin:
        erro = "Você não pode retirar o seu próprio perfil de administrador."
    if erro:
        db.rollback()
        return render(request, "conta/usuario.html", **_form_ctx(db, c, db.get(Usuario, id), erro=erro))
    db.commit()
    return voltar("/usuarios", f"Usuário {u.nome} atualizado.")


@router.post("/usuarios/{id}/senha")
def usuario_nova_senha(request: Request, id: int, db: Session = Depends(get_db)):
    c = request.state.usuario
    u = db.get(Usuario, id)
    if not u or not _pode_editar(c, u):
        return voltar("/usuarios", erro="Usuário não encontrado ou fora do seu perfil.")
    senha = acesso.senha_provisoria()
    u.senha_hash = acesso.gerar_hash(senha)
    u.trocar_senha = True
    db.commit()
    return render(request, "conta/senha_gerada.html", u=u, senha=senha, novo=False, menu="usuarios")


@router.post("/usuarios/{id}/excluir")
def usuario_excluir(request: Request, id: int, db: Session = Depends(get_db)):
    c = request.state.usuario
    u = db.get(Usuario, id)
    if not u or not _pode_editar(c, u) or u.id == c.id:
        return voltar("/usuarios", erro="Não é possível excluir este usuário.")
    db.delete(u)
    db.commit()
    return voltar("/usuarios", "Usuário excluído.")


# ------------------------------------------------------------------ histórico (admin)
@router.get("/historico")
def historico(request: Request, q: str = "", db: Session = Depends(get_db)):
    qs = select(Acao).order_by(Acao.id.desc()).limit(300)
    if q:
        qs = select(Acao).where(or_(Acao.login.ilike(f"%{q}%"), Acao.descricao.ilike(f"%{q}%"), Acao.caminho.ilike(f"%{q}%"),
                                    Acao.detalhe.ilike(f"%{q}%"))).order_by(Acao.id.desc()).limit(300)
    return render(request, "conta/historico.html", acoes=db.scalars(qs).all(), q=q, menu="historico")


# ------------------------------------------------------------------ situação da turma
def _status(db: Session, tid: int) -> TurmaStatus:
    st = acesso.status_turma(db, tid)
    if not st:
        st = TurmaStatus(turma_id=tid)
        db.add(st)
    return st


@router.post("/turmas/{tid}/encerrar")
def encerrar(request: Request, tid: int, db: Session = Depends(get_db)):
    st = _status(db, tid)
    st.encerrada_em, st.encerrada_por = datetime.now(), request.state.usuario.login
    db.commit()
    return voltar(f"/turmas/{tid}", "Turma encerrada: agora é somente leitura para professores e alunos.")


@router.post("/turmas/{tid}/reabrir")
def reabrir(tid: int, db: Session = Depends(get_db)):
    st = _status(db, tid)
    st.encerrada_em = st.encerrada_por = None
    db.commit()
    return voltar(f"/turmas/{tid}", "Turma reaberta.")


@router.post("/turmas/{tid}/demonstracao")
def demonstracao(tid: int, db: Session = Depends(get_db)):
    st = _status(db, tid)
    st.demonstracao = not st.demonstracao
    db.commit()
    return voltar(f"/turmas/{tid}", "Turma marcada como demonstração: visitantes podem vê-la." if st.demonstracao
                  else "A turma deixou de ser de demonstração.")
