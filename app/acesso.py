"""Etapa 7 · Login com perfis, regras de acesso, turma encerrada/demonstração e histórico de ações.

Perfis
  admin        acesso total, inclusive operações em lote e histórico;
  coordenador  cadastros (disciplinas, docentes, discentes, turmas, importação), caso-base, base normativa,
               usuários professor/monitor/visitante;
  professor    suas turmas (vínculo docente ↔ turma): duplas, empresas, códigos, escrituração, tutor;
               caso-base para consulta e a própria cópia do caso (inclusive premissas do gabarito);
  monitor      acompanha as turmas atribuídas, só leitura, sem gabarito e sem cadastros pessoais;
  visitante    avaliadores: só leitura, apenas nas turmas marcadas como demonstração;
  aluno        área /aluno do próprio grupo (matrícula + senha).

Tabelas novas (create_all): usuarios, usuario_perfis, turma_status, historico_acoes.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from .config import APP_SENHA, APP_USUARIO
from .db import Base
from . import models  # noqa: F401

PERFIS = {"admin": "Administrador", "coordenador": "Coordenador", "professor": "Professor",
          "monitor": "Monitor", "visitante": "Visitante (avaliador)", "aluno": "Aluno"}
EQUIPE = ("admin", "coordenador", "professor", "monitor", "visitante")
ESCOPADOS = ("professor", "monitor", "visitante")
SO_LEITURA = ("monitor", "visitante")
COOKIE = "labcont_sessao"
COOKIE_VER = "labcont_ver"  # equipe vendo a área do aluno de um grupo (somente leitura)
_SEGREDO = (os.getenv("SECRET_KEY") or hashlib.sha256(f"{APP_SENHA}|labcont-aluno".encode()).hexdigest()).encode()


# ------------------------------------------------------------------ tabelas
class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(160), unique=True, index=True)  # e-mail/login da equipe ou matrícula do aluno
    nome: Mapped[str] = mapped_column(String(200))
    senha_hash: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    trocar_senha: Mapped[bool] = mapped_column(Boolean, default=False)
    docente_id: Mapped[int | None] = mapped_column(ForeignKey("docentes.id", ondelete="SET NULL"))
    discente_id: Mapped[int | None] = mapped_column(ForeignKey("discentes.id", ondelete="CASCADE"))
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime)

    perfis: Mapped[list[UsuarioPerfil]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    docente = relationship("Docente")
    discente = relationship("Discente")

    @property
    def nomes_perfis(self) -> set[str]:
        return {p.perfil for p in self.perfis}

    @property
    def e_gestor(self) -> bool:
        return bool(self.nomes_perfis & {"admin", "coordenador"})


class UsuarioPerfil(Base):
    """Um perfil do usuário. turma_id só é usado no perfil monitor (turmas que ele acompanha)."""
    __tablename__ = "usuario_perfis"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    perfil: Mapped[str] = mapped_column(String(20))
    turma_id: Mapped[int | None] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"))


class TurmaStatus(Base):
    """Situação da turma sem alterar a tabela 'turmas': encerrada (somente leitura) e/ou de demonstração."""
    __tablename__ = "turma_status"
    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id", ondelete="CASCADE"), unique=True)
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime)
    encerrada_por: Mapped[str | None] = mapped_column(String(160))
    demonstracao: Mapped[bool] = mapped_column(Boolean, default=False)


class Acao(Base):
    __tablename__ = "historico_acoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    quando: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer)
    login: Mapped[str] = mapped_column(String(160), default="")
    perfil: Mapped[str] = mapped_column(String(100), default="")
    metodo: Mapped[str] = mapped_column(String(10), default="POST")
    caminho: Mapped[str] = mapped_column(String(300), default="")
    descricao: Mapped[str] = mapped_column(String(300), default="")
    detalhe: Mapped[str | None] = mapped_column(Text)


# ------------------------------------------------------------------ senhas e sessão
def gerar_hash(senha: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), 200_000).hex()
    return f"pbkdf2${sal}${h}"


def conferir(senha: str, guardado: str) -> bool:
    try:
        _, sal, h = guardado.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), 200_000).hex(), h)


def senha_provisoria() -> str:
    alfa = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(alfa) for _ in range(4)) for _ in range(3))


def validar_senha(s: str) -> str | None:
    if len(s or "") < 8:
        return "A senha precisa ter pelo menos 8 caracteres."
    return None


def assinar(valor: str) -> str:
    return hmac.new(_SEGREDO, valor.encode(), hashlib.sha256).hexdigest()[:32]


def cookie_sessao(u: Usuario) -> str:
    v = f"{u.id}.{int(time.time())}.{u.senha_hash[-10:]}"
    return f"{u.id}.{int(time.time())}.{assinar(v)}"


DURACAO = {"aluno": 60 * 60 * 24 * 14, "equipe": 60 * 60 * 12}


def ler_sessao(db: Session, bruto: str) -> Usuario | None:
    try:
        uid, ts, sig = bruto.split(".")
        uid, ts = int(uid), int(ts)
    except (ValueError, AttributeError):
        return None
    u = db.get(Usuario, uid)
    if not u or not u.ativo or not hmac.compare_digest(sig, assinar(f"{uid}.{ts}.{u.senha_hash[-10:]}")):
        return None
    limite = DURACAO["aluno"] if u.nomes_perfis == {"aluno"} else DURACAO["equipe"]
    return u if time.time() - ts < limite else None


def https(request) -> bool:
    return request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"


# ------------------------------------------------------------------ contexto do usuário
@dataclass
class Ctx:
    id: int | None
    login: str
    nome: str
    perfis: set[str]
    docente_id: int | None = None
    discente_id: int | None = None
    trocar_senha: bool = False
    turmas: set[int] = field(default_factory=set)        # turmas do escopo (professor/monitor/visitante)
    turmas_prof: set[int] = field(default_factory=set)   # turmas em que é professor (pode alterar)
    turmas_monitor: set[int] = field(default_factory=set)
    turmas_demo: set[int] = field(default_factory=set)
    dev: bool = False                                    # modo aberto (sem usuários cadastrados)

    @property
    def admin(self) -> bool:
        return "admin" in self.perfis

    @property
    def gestor(self) -> bool:
        return bool({"admin", "coordenador"} & self.perfis)

    @property
    def equipe(self) -> bool:
        return bool(set(EQUIPE) & self.perfis)

    @property
    def so_leitura(self) -> bool:
        return self.equipe and not ({"admin", "coordenador", "professor"} & self.perfis)

    @property
    def todas_turmas(self) -> bool:
        return self.gestor

    def ve_turma(self, tid: int | None) -> bool:
        return tid is not None and (self.gestor or tid in self.turmas)

    def altera_turma(self, tid: int | None) -> bool:
        return tid is not None and (self.gestor or tid in self.turmas_prof)

    @property
    def rotulo_perfis(self) -> str:
        return ", ".join(PERFIS[p] for p in EQUIPE + ("aluno",) if p in self.perfis)


def montar_ctx(db: Session, u: Usuario) -> Ctx:
    from .models import TurmaDocente
    perfis = u.nomes_perfis
    c = Ctx(u.id, u.login, u.nome, perfis, u.docente_id, u.discente_id, u.trocar_senha)
    if "professor" in perfis and u.docente_id:
        c.turmas_prof = set(db.scalars(select(TurmaDocente.turma_id).where(TurmaDocente.docente_id == u.docente_id)).all())
        c.turmas |= c.turmas_prof
    if "monitor" in perfis:
        c.turmas_monitor = {p.turma_id for p in u.perfis if p.perfil == "monitor" and p.turma_id}
        c.turmas |= c.turmas_monitor
    if "visitante" in perfis:
        c.turmas_demo = turmas_demonstracao(db)
        c.turmas |= c.turmas_demo
    return c


def ctx_dev() -> Ctx:
    return Ctx(None, "dev", "Modo local", {"admin"}, dev=True)


def tem_equipe(db: Session) -> bool:
    return db.scalar(select(UsuarioPerfil.id).where(UsuarioPerfil.perfil.in_(EQUIPE)).limit(1)) is not None


def modo_aberto(db: Session) -> bool:
    """Sem usuário de equipe e sem APP_USUARIO/APP_SENHA: ambiente local de desenvolvimento e testes."""
    return not (APP_USUARIO and APP_SENHA) and not tem_equipe(db)


def garantir_admin(db: Session) -> None:
    """Na primeira subida com login, cria o administrador a partir de APP_USUARIO/APP_SENHA do .env."""
    if APP_USUARIO and APP_SENHA and not tem_equipe(db):
        u = db.scalar(select(Usuario).where(Usuario.login == APP_USUARIO.lower()))
        if not u:
            u = Usuario(login=APP_USUARIO.lower(), nome="Administrador", senha_hash=gerar_hash(APP_SENHA))
            db.add(u)
            db.flush()
        u.perfis.append(UsuarioPerfil(perfil="admin"))
        db.commit()


# ------------------------------------------------------------------ turmas: encerrada e demonstração
def status_turma(db: Session, tid: int) -> TurmaStatus | None:
    return db.scalar(select(TurmaStatus).where(TurmaStatus.turma_id == tid))


def turma_encerrada(db: Session, tid: int | None) -> bool:
    st = status_turma(db, tid) if tid else None
    return bool(st and st.encerrada_em)


def turmas_demonstracao(db: Session) -> set[int]:
    return set(db.scalars(select(TurmaStatus.turma_id).where(TurmaStatus.demonstracao.is_(True))).all())


# ------------------------------------------------------------------ regras
A, C, P, M, V = "admin", "coordenador", "professor", "monitor", "visitante"
G = ("GET", "HEAD")
X = ("POST",)
GX = G + X
# (padrão, métodos, perfis que podem, observação). Grupos nomeados resolvem o escopo:
#   tid = turma · did = dupla · cid = caso · dis = discente.  O admin pode tudo.
REGRAS: list[tuple[str, tuple, tuple, str]] = [
    (r"^/$", G, (C, P, M, V), ""),
    (r"^/conta/senha$", GX, (C, P, M, V), ""),
    (r"^/disciplinas(/.*)?$", GX, (C,), ""),
    (r"^/docentes(/.*)?$", GX, (C,), ""),
    (r"^/discentes/(?P<dis>\d+)$", G, (C, P), ""),
    (r"^/discentes(/.*)?$", GX, (C,), ""),
    (r"^/importacao(/.*)?$", GX, (C,), ""),
    (r"^/turmas/nova$", GX, (C,), ""),
    (r"^/turmas/(?P<tid>\d+)$", G, (C, P, M, V), ""),
    (r"^/turmas/(?P<tid>\d+)/encerrar$", X, (C,), ""),
    (r"^/turmas/(?P<tid>\d+)/(reabrir|demonstracao)$", X, (), "só admin"),
    (r"^/turmas/(?P<tid>\d+)/(painel|duplas)$", G, (C, P, M, V), ""),
    (r"^/turmas/(?P<tid>\d+)/notas(\.csv)?$", G, (C, P, V), ""),
    (r"^/turmas/(?P<tid>\d+)/notas$", X, (C, P), ""),
    (r"^/turmas/(?P<tid>\d+)/duplas(/lote|/gerar|/codigos)?$", X, (C, P), ""),
    (r"^/turmas/(?P<tid>\d+)/(duplas\.csv|duplas/orientacoes\.zip)$", G, (C, P), ""),
    (r"^/turmas/(?P<tid>\d+)/alunos/(?P<dis>\d+)/senha$", X, (C, P), ""),
    (r"^/turmas/(?P<tid>\d+)/.*$", GX, (C,), ""),
    (r"^/duplas$", G, (C, P, M, V), ""),
    (r"^/duplas/(?P<did>\d+)/gabarito(\.xlsx)?$", G, (C, P, V), ""),
    (r"^/duplas/(?P<did>\d+)/.*$", G, (C, P, M, V), ""),
    (r"^/duplas/(?P<did>\d+)/.*$", X, (C, P), ""),
    (r"^/casos$", G, (C, P, V), ""),
    (r"^/casos/(carregar|importar)$", X, (C,), ""),
    (r"^/casos/(?P<cid>\d+)/duplicar$", X, (C, P), "ler"),
    (r"^/casos/(?P<cid>\d+)(/.*)?$", G, (C, P, V), "ler"),
    (r"^/casos/(?P<cid>\d+)(/.*)?$", X, (C, P), "alterar"),
    (r"^/normas(/.*)?$", G, (C, P, M, V), ""),
    (r"^/normas(/.*)?$", X, (C,), ""),
    (r"^/usuarios(/.*)?$", GX, (C,), ""),
    (r"^/aluno/ver/(?P<did>\d+)$", G, (C, P, M, V), ""),
    (r"^/(historico|admin)(/.*)?$", GX, (), "só admin"),
]
_REGRAS = [(re.compile(p), m, papeis, obs) for p, m, papeis, obs in REGRAS]


def _turma_da_dupla(db: Session, did: int) -> int | None:
    from .models_dupla import Dupla
    d = db.get(Dupla, did)
    return d.turma_id if d else None


def _turmas_do_discente(db: Session, dis: int) -> set[int]:
    from .models import Matricula
    return set(db.scalars(select(Matricula.turma_id).where(Matricula.discente_id == dis)).all())


def autorizar(db: Session, c: Ctx, metodo: str, caminho: str) -> tuple[bool, str, int | None]:
    """Devolve (permitido, motivo, turma_id resolvida)."""
    metodo = "GET" if metodo == "HEAD" else metodo
    for rx, metodos, papeis, obs in _REGRAS:
        m = rx.match(caminho)
        if not m or metodo not in metodos:
            continue
        g = m.groupdict()
        tid = int(g["tid"]) if g.get("tid") else (_turma_da_dupla(db, int(g["did"])) if g.get("did") else None)
        if g.get("tid") or g.get("did"):
            if tid is None:
                return False, "Registro não encontrado.", None
        if metodo == "POST" and tid and turma_encerrada(db, tid) and not c.admin:
            return False, "Turma encerrada: somente leitura. Só o administrador pode alterar.", tid
        if c.admin:
            return True, "", tid
        for papel in papeis:
            if papel not in c.perfis:
                continue
            if papel in SO_LEITURA and metodo == "POST":
                continue
            if papel == C:
                return True, "", tid
            # professor, monitor, visitante: só dentro do escopo
            if tid is not None:
                if tid in {P: c.turmas_prof, M: c.turmas_monitor, V: c.turmas_demo}[papel]:
                    return True, "", tid
                continue
            if g.get("dis"):
                if _turmas_do_discente(db, int(g["dis"])) & c.turmas_prof:
                    return True, "", None
                continue
            if g.get("cid"):
                from .models_caso import Caso
                caso = db.get(Caso, int(g["cid"]))
                if not caso:
                    return False, "Caso não encontrado.", None
                if papel == V and obs == "ler":
                    return True, "", None
                if papel == P and obs == "ler" and (caso.docente_id is None or caso.docente_id == c.docente_id):
                    return True, "", None
                if papel == P and obs == "alterar" and caso.docente_id and caso.docente_id == c.docente_id:
                    return True, "", None
                continue
            return True, "", None
        return False, "Seu perfil não tem acesso a esta área.", tid
    return (True, "", None) if c.admin else (False, "Seu perfil não tem acesso a esta área.", None)


# ------------------------------------------------------------------ histórico
DESCRICOES = [
    (r"^/entrar$", "Entrou no sistema"), (r"^/aluno/entrar$", "Aluno entrou"), (r"^/aluno/primeiro-acesso$", "Aluno criou a senha"),
    (r"/excluir$", "Excluiu"), (r"/editar$", "Alterou"), (r"/(nova|novo)$", "Incluiu"), (r"^/aluno/lancar$", "Lançamento da dupla"),
    (r"^/aluno/fechamento$", "Enviou o fechamento de janeiro"), (r"^/aluno/tutor$", "Pergunta ao tutor"),
    (r"/fechamento/reabrir$", "Reabriu o fechamento da dupla"), (r"/encerrar$", "Encerrou a turma"), (r"/reabrir$", "Reabriu a turma"),
    (r"/demonstracao$", "Alterou a marcação de demonstração"), (r"/codigos$|/codigo/novo$", "Gerou códigos de acesso"),
    (r"/senha$", "Senha"), (r"^/admin/lote", "Operação em lote"), (r"/gerar$", "Gerou empresas"), (r"^/importacao", "Importação do SIGAA"),
    (r"^/usuarios", "Usuários"), (r"^/casos", "Caso da empresa"), (r"^/normas", "Base normativa"),
]


def descrever(caminho: str) -> str:
    for p, d in DESCRICOES:
        if re.search(p, caminho):
            return d
    return "Alteração"


def registrar(db: Session, c: Ctx | None, caminho: str, descricao: str | None = None, detalhe: str | None = None,
              metodo: str = "POST", login: str | None = None) -> None:
    db.add(Acao(usuario_id=c.id if c else None, login=(login or (c.login if c else "")), perfil=(c.rotulo_perfis if c else ""),
                metodo=metodo, caminho=caminho[:300], descricao=(descricao or descrever(caminho))[:300], detalhe=detalhe))
    db.commit()


# ------------------------------------------------------------------ tentativas de login
_FALHAS: dict[str, list[float]] = {}


def bloqueado(chave: str) -> bool:
    agora = time.time()
    _FALHAS[chave] = [t for t in _FALHAS.get(chave, []) if agora - t < 300]
    return len(_FALHAS[chave]) >= 5


def falhou(chave: str) -> None:
    _FALHAS.setdefault(chave, []).append(time.time())


def limpar_falhas(chave: str) -> None:
    _FALHAS.pop(chave, None)
