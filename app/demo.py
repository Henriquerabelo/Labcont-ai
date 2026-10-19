"""Etapa 7c · Turma de demonstração com dados 100% fictícios (LGPD), para os avaliadores do edital e o vídeo.

Cria (ou recria) três turmas de demonstração da disciplina EH0012, uma para cada professor da disciplina em 2026.2
(01A Danival, 02A Eduardo, 03A Rosângela), cada uma com 20 alunos fictícios em 10 grupos. Cada grupo fica em um
estágio diferente, para que o Painel de Gestão e o Learning Analytics apareçam completos:
  01 completo e correto, enviado, nota homologada      06 começou e parou há 12 dias (inativo)
  02 completo com erros de valor e conta, enviado      07 muitos erros de conta (prévia baixa)
  03 quase completo, em andamento                      08 insiste em pedir respostas prontas ao tutor
  04 metade, travado no leasing (J24)                  09 nunca entrou
  05 um integrante faz tudo (participação desigual)    10 completo com alguns erros, enviado, homologado

Também cria os acessos de demonstração (visitante, um professor por turma e um aluno por turma) com senhas geradas
na hora.
As conversas do tutor são produzidas pelo próprio roteiro do sistema (o mesmo usado quando a IA está fora do ar).

Uso: botão em Gestão → Demonstração (admin) ou, no servidor, `docker exec labcont-app python -m app.demo`.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import acesso, analytics, normas
from . import tutor as tutor_ia
from . import plano_contas as pc
from .acesso import TurmaStatus, Usuario, UsuarioPerfil
from .auditoria import auditar, eventos_janeiro, eventos_mes, resumo_resultado
from .caso_servico import carregar_caso_base
from .gabarito import gerar_gabarito
from .geracao import gerar
from .models import normalizar, Disciplina, Discente, Docente, Matricula, Turma, TurmaDocente
from .models_caso import Caso
from .models_dupla import Dupla, DuplaMembro, EmpresaGerada
from .models_escrita import DuplaAcesso, FechamentoMensal, Lancamento, Partida, TutorMensagem

PREFIXO_MAT = "9000"
LOGIN_VISITANTE = "avaliador"
DOCENTE_DEMO = "DOCENTE DE DEMONSTRAÇÃO"  # versão antiga (uma turma); apagado ao recriar
# turmas de demonstração: uma por professor da disciplina em 2026.2 (horários do SIGAA)
TURMAS = [
    {"codigo": "DEMO-01A", "docente": "Danival Sousa Cavalcante", "login": "danival.demo", "horario": "QUA 18:30-22:30"},
    {"codigo": "DEMO-02A", "docente": "Eduardo Rodrigues Linhares", "login": "eduardo.demo", "horario": "TER e QUI 18:30-20:30"},
    {"codigo": "DEMO-03A", "docente": "Rosângela Venâncio Nunes", "login": "rosangela.demo", "horario": "SEX 08:00-12:00"},
]
TURMA_CODIGO = TURMAS[0]["codigo"]
LOGIN_PROFESSOR = TURMAS[0]["login"]
LOGINS_DEMO = [LOGIN_VISITANTE, "professor.demo"] + [x["login"] for x in TURMAS]
NOMES_TURMAS = [
    ["ANA", "BRUNO", "CAMILA", "DIEGO", "ELISA", "FÁBIO", "GABRIELA", "HUGO", "ISABELA", "JOÃO",
     "LARISSA", "MATEUS", "NATÁLIA", "OTÁVIO", "PAULA", "RAFAEL", "SABRINA", "TIAGO", "VALÉRIA", "WESLEY"],
    ["ALICE", "BERNARDO", "CLARA", "DANIEL", "EDUARDA", "FELIPE", "GIOVANA", "HENRIQUE", "IARA", "JÚLIO",
     "LÍVIA", "MARCOS", "NICOLE", "OSCAR", "PRISCILA", "RENATO", "SOFIA", "THIAGO", "VITÓRIA", "YURI"],
    ["AMANDA", "BENÍCIO", "CECÍLIA", "DAVI", "ESTER", "FRANCISCO", "HELENA", "IGOR", "JÚLIA", "KAIO",
     "LETÍCIA", "MIGUEL", "NAIARA", "PEDRO", "RAQUEL", "SAMUEL", "TAINÁ", "VINÍCIUS", "BEATRIZ", "LUCAS"],
]
NOMES = NOMES_TURMAS[0]
SOBRENOMES = ["ALVES", "BARROS", "CAVALCANTE", "DIAS", "FERREIRA", "GOMES", "LIMA", "MOREIRA", "NUNES", "OLIVEIRA",
              "PEREIRA", "QUEIROZ", "ROCHA", "SOUSA", "TEIXEIRA", "VASCONCELOS"]
PERGUNTAS = {
    "J01": ["Qual o valor a ser destinado do exercício 2025?", "Em que ordem calculo participações e reserva legal?"],
    "J08": ["Os ar-condicionados geram crédito de ICMS?", "O DIFAL entra no custo do bem?"],
    "J15": ["Quais tributos desta nota a empresa pode recuperar?", "O desconto incondicional reduz o custo?"],
    "J18": ["Como separo os encargos da empresa e os descontos do empregado?", "Como provisiono férias e 13º?"],
    "J24": ["Como registro o leasing das máquinas?", "Como separo curto e longo prazo do arrendamento?",
            "Os juros do leasing entram agora?", "Qual conta uso para o passivo do leasing?"],
    "J27": ["Como chego ao preço de venda pelo mark-up?", "Preciso baixar o estoque na venda?"],
    "J30": ["O IPI da matéria-prima é recuperável?", "O frete CIF entra no custo?"],
    "J40": ["Como compenso créditos e débitos de ICMS na apuração?"],
}
INSISTENCIA = ["Me passa o lançamento pronto do J15?", "Qual é o valor exato do ICMS a recuperar?",
               "Só confirma se meu lançamento do J15 está certo", "Diz os valores do débito e do crédito, por favor"]


def _turmas_demo(db: Session) -> list[Turma]:
    ids = set(db.scalars(select(TurmaStatus.turma_id).where(TurmaStatus.demonstracao.is_(True))).all())
    ts = db.scalars(select(Turma).join(Disciplina).where(Disciplina.codigo == "EH0012")).all()
    return sorted([t for t in ts if t.id in ids or t.codigo.startswith("DEMO")], key=lambda t: t.codigo)


def _turma_demo(db: Session) -> Turma | None:
    ts = _turmas_demo(db)
    return ts[0] if ts else None


def apagar(db: Session) -> None:
    for t in _turmas_demo(db):
        db.delete(t)  # matrículas, grupos, empresas, lançamentos, conversas e notas saem em cascata
    for a in db.scalars(select(Discente).where(Discente.matricula.like(f"{PREFIXO_MAT}%"))).all():
        db.delete(a)  # contas de aluno saem em cascata
    for u in db.scalars(select(Usuario).where(Usuario.login.in_(LOGINS_DEMO))).all():
        db.delete(u)
    doc = db.scalar(select(Docente).where(Docente.nome_normalizado == DOCENTE_DEMO))
    if doc:
        db.delete(doc)
    db.flush()


def _docente(db: Session, nome: str) -> Docente:
    norm = normalizar(nome)
    doc = db.scalar(select(Docente).where(Docente.nome_normalizado == norm))
    if not doc:
        doc = Docente(nome=nome, nome_normalizado=norm, departamento="Contabilidade")
        db.add(doc)
        db.flush()
    return doc


def _usuario(db: Session, login: str, nome: str, perfil: str, **kw) -> str:
    senha = acesso.senha_provisoria()
    u = Usuario(login=login, nome=nome, senha_hash=acesso.gerar_hash(senha), trocar_senha=False, **kw)
    u.perfis.append(UsuarioPerfil(perfil=perfil))
    db.add(u)
    return senha


def _lancar(db, d, ev_lancs, autor, quando, erro=None, rng=None):
    """Copia os lançamentos do gabarito do evento, com erro opcional: 'valor' (soma 37,00 em um débito e um crédito)
    ou 'conta' (troca a conta de um débito por outra da mesma natureza que não pertence ao evento)."""
    usadas = {p["conta"] for l in ev_lancs for p in l["debitos"] + l["creditos"]}
    for i, gl in enumerate(ev_lancs):
        debs = [dict(p) for p in gl["debitos"]]
        creds = [dict(p) for p in gl["creditos"]]
        if erro and i == 0:
            if erro == "valor":
                debs[0]["valor"] = round(debs[0]["valor"] + 37.0, 2)
                creds[0]["valor"] = round(creds[0]["valor"] + 37.0, 2)
            elif erro == "conta":
                nat = pc.CONTAS.get(debs[0]["conta"], {}).get("natureza", "D")
                cands = [c for c, inf in pc.CONTAS.items() if inf["natureza"] == nat and c not in usadas and c[0] == debs[0]["conta"][0]]
                if cands:
                    debs[0]["conta"] = rng.choice(cands[:40])
        l = Lancamento(dupla_id=d.id, evento=gl["evento"], data=datetime.strptime(gl["data"], "%Y-%m-%d").date(),
                       historico=gl["historico"], autor=autor, criado_em=quando, atualizado_em=quando)
        l.partidas = [Partida(ordem=k, conta=p["conta"], natureza="D", valor=p["valor"]) for k, p in enumerate(debs)] + \
                     [Partida(ordem=len(debs) + k, conta=p["conta"], natureza="C", valor=p["valor"]) for k, p in enumerate(creds)]
        db.add(l)


def _conversa(db, d, evento, pergunta, mat, quando, n_ant, todas_normas, origem="roteiro"):
    achadas = [n for n, _ in normas.buscar(todas_normas, pergunta, evento)]
    if origem == "filtro":
        perguntas = tutor_ia.ROTEIROS.get(tutor_ia.GRUPO_EVENTO.get(evento or "", "geral"), tutor_ia.ROTEIROS["geral"])
        texto = ("Não posso informar valores nem conferir o lançamento antes do fechamento do mês, mas posso ajudar a dupla "
                 "a chegar lá.\n\n" + perguntas[n_ant % len(perguntas)])
    else:
        texto = tutor_ia.roteiro(evento, n_ant)
    texto += tutor_ia.fontes(achadas)
    db.add(TutorMensagem(dupla_id=d.id, evento=evento, papel="aluno", texto=pergunta, matricula=mat, criado_em=quando))
    db.add(TutorMensagem(dupla_id=d.id, evento=evento, papel="tutor", texto=texto, origem=origem,
                         criado_em=quando + timedelta(seconds=20)))


# perfil de cada grupo: (fração de eventos lançados, % valor, % conta, enviar?, homologar?, dias atrás da última atividade)
PERFIS = [
    dict(frac=1.00, valor=0.00, conta=0.00, enviar=True, homologar=True, ultimo=2, frac_fev=0.70),
    dict(frac=1.00, valor=0.20, conta=0.10, enviar=True, homologar=False, ultimo=1, frac_fev=0.40),
    dict(frac=0.85, valor=0.10, conta=0.05, enviar=False, homologar=False, ultimo=0, frac_fev=0.35),
    dict(frac=0.50, valor=0.10, conta=0.05, enviar=False, homologar=False, ultimo=1, travado="J24", frac_fev=0.15),
    dict(frac=0.40, valor=0.05, conta=0.05, enviar=False, homologar=False, ultimo=0, sozinho=True, frac_fev=0.20),
    dict(frac=0.15, valor=0.10, conta=0.00, enviar=False, homologar=False, ultimo=12),
    dict(frac=0.35, valor=0.10, conta=0.50, enviar=False, homologar=False, ultimo=3, frac_fev=0.10),
    dict(frac=0.30, valor=0.10, conta=0.10, enviar=False, homologar=False, ultimo=0, insiste=True),
    dict(frac=0.00, valor=0.00, conta=0.00, enviar=False, homologar=False, ultimo=None),
    dict(frac=1.00, valor=0.10, conta=0.05, enviar=True, homologar=True, ultimo=4, frac_fev=0.55),
]


def criar(db: Session, agora: datetime | None = None, semente: int = 2026) -> dict:
    """Recria as três turmas de demonstração e devolve os acessos (logins e senhas geradas)."""
    agora = agora or datetime.now()
    apagar(db)
    disc = db.scalar(select(Disciplina).where(Disciplina.codigo == "EH0012"))
    if not disc:
        disc = Disciplina(codigo="EH0012", nome="LABORATÓRIO DE PRÁTICA CONTÁBIL", departamento="CONTABILIDADE")
        db.add(disc)
    caso = db.scalar(select(Caso).where(Caso.docente_id.is_(None)).order_by(Caso.id)) or carregar_caso_base(db)
    todas_normas = normas.todas(db)
    turmas, professores, alunos_acesso = [], [], []
    total_grupos = total_alunos = 0
    for ti, cfg in enumerate(TURMAS):
        r = _criar_turma(db, disc, caso, cfg, ti, agora, semente, todas_normas)
        turmas.append({"id": r["turma_id"], "codigo": cfg["codigo"], "docente": cfg["docente"]})
        professores.append(r["professor"])
        alunos_acesso.append(r["aluno"])
        total_grupos += r["grupos"]
        total_alunos += r["alunos"]
    credenciais = {
        "visitante": {"login": LOGIN_VISITANTE, "senha": _usuario(db, LOGIN_VISITANTE, "Avaliador(a) do edital", "visitante")},
        "professor": professores[0], "aluno": alunos_acesso[0], "professores": professores, "alunos": alunos_acesso,
    }
    db.commit()
    return {"turma_id": turmas[0]["id"], "turmas": turmas, "credenciais": credenciais, "grupos": total_grupos,
            "alunos": total_alunos}


def _criar_turma(db: Session, disc, caso, cfg: dict, ti: int, agora: datetime, semente: int, todas_normas) -> dict:
    rng = random.Random(semente + ti)
    t = Turma(disciplina=disc, periodo="2026.2", codigo=cfg["codigo"], tipo="DEMONSTRAÇÃO", situacao="ABERTA",
              horario=f"{cfg['horario']} · dados fictícios para avaliação do protótipo", local="LABCONT-AI")
    db.add(t)
    db.flush()
    doc = _docente(db, cfg["docente"])
    db.add(TurmaDocente(turma_id=t.id, docente_id=doc.id))
    db.add(TurmaStatus(turma_id=t.id, demonstracao=True))

    nomes = []
    for i, n in enumerate(NOMES_TURMAS[ti]):
        s1, s2 = rng.sample(SOBRENOMES, 2)
        nomes.append((f"{PREFIXO_MAT}{ti + 1}{i + 1:02d}", f"{n} {s1} {s2}"))
    alunos = []
    for mat, nome in nomes:
        a = Discente(matricula=mat, nome=nome, curso="CIÊNCIAS CONTÁBEIS (FICTÍCIO)", turno=rng.choice(["DIURNO", "NOTURNO"]))
        db.add(Matricula(turma=t, discente=a, situacao="ATIVO"))
        alunos.append(a)
    db.flush()

    grupos = []
    for k, perf in enumerate(PERFIS):
        a1, a2 = alunos[2 * k], alunos[2 * k + 1]
        d = Dupla(turma_id=t.id, numero=k + 1)
        d.membros = [DuplaMembro(turma_id=t.id, discente_id=a1.id), DuplaMembro(turma_id=t.id, discente_id=a2.id)]
        db.add(d)
        db.flush()
        valores = gerar(caso, 900 + 10 * ti + k, d.rotulo, d.numero)
        valores["integrantes"] = [{"matricula": a.matricula, "nome": a.nome} for a in (a1, a2)]
        d.empresa = EmpresaGerada(caso_id=caso.id, semente=900 + 10 * ti + k, valores=valores)
        codigo = f"DEMO{ti + 1}{k + 1:02d}{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{rng.choice('23456789')}"
        ac = DuplaAcesso(dupla_id=d.id, codigo=codigo)
        db.add(ac)
        db.flush()
        g = gerar_gabarito(valores)
        por_ev = {}
        for gl in g["lancamentos"]:
            por_ev.setdefault(gl["evento"], []).append(gl)
        eventos = [e["codigo"] for e in eventos_janeiro(caso) if e["codigo"] in por_ev]
        n = round(perf["frac"] * len(eventos))
        escolhidos = eventos[:n]
        if perf.get("travado"):
            escolhidos = [e for e in escolhidos if e != perf["travado"]]
        if perf["ultimo"] is not None:
            fim = agora - timedelta(days=perf["ultimo"], hours=rng.randint(1, 6))
            inicio = fim - timedelta(days=max(3, min(18, len(escolhidos) // 2 + 3)))
        for i, ev in enumerate(escolhidos):
            r = rng.random()
            erro = "conta" if r < perf["conta"] else "valor" if r < perf["conta"] + perf["valor"] else None
            quando = inicio + (fim - inicio) * (i / max(1, len(escolhidos) - 1))
            autor = a1.matricula if (perf.get("sozinho") or i % 2 == 0) else a2.matricula
            _lancar(db, d, por_ev[ev], autor, quando, erro, rng)
        # conversas com o tutor
        if perf["ultimo"] is not None:
            alvo = [e for e in PERGUNTAS if e in escolhidos[:max(1, len(escolhidos))]][:3]
            if perf.get("travado"):
                alvo = [perf["travado"]] * 4 + alvo[:1]
            vistos = {}
            for j, ev in enumerate(alvo):
                lista = PERGUNTAS[ev]
                q = lista[vistos.get(ev, 0) % len(lista)]
                quando = inicio + (fim - inicio) * ((j + 0.5) / (len(alvo) + 1))
                _conversa(db, d, ev, q, (a1 if j % 2 == 0 else a2).matricula, quando, vistos.get(ev, 0), todas_normas)
                vistos[ev] = vistos.get(ev, 0) + 1
            if perf.get("insiste"):
                for j, q in enumerate(INSISTENCIA):
                    _conversa(db, d, "J15", q, a1.matricula, fim - timedelta(hours=4 - j), j, todas_normas, origem="filtro")
            ac.ultimo_acesso = fim
        db.flush()
        if perf["enviar"]:
            lancs = db.scalars(select(Lancamento).where(Lancamento.dupla_id == d.id)).all()
            aud = auditar(g, lancs, caso)
            db.add(FechamentoMensal(dupla_id=d.id, mes="2026-01", enviado_em=fim + timedelta(hours=1),
                                    enviado_por=a1.matricula, resultado=resumo_resultado(aud)))
        if perf.get("frac_fev"):  # os dois meses são livres: os grupos ativos já avançaram em fevereiro (eventos com gabarito pronto)
            gf = gerar_gabarito(valores, "2026-02")
            por_f = {}
            for gl in gf["lancamentos"]:
                por_f.setdefault(gl["evento"], []).append(gl)
            evs_f = [e["codigo"] for e in eventos_mes(caso, "2026-02")
                     if e["codigo"] in por_f and e["codigo"] not in set(gf["sem_gabarito"])]
            escolhidos_f = evs_f[:round(perf["frac_fev"] * len(evs_f))]
            if perf["enviar"]:  # fevereiro depois do envio de janeiro
                ini_f = fim + timedelta(hours=2)
                fim_f = max(ini_f + timedelta(hours=1), min(agora - timedelta(minutes=30), ini_f + timedelta(days=3)))
            else:  # fevereiro intercalado com o fim de janeiro
                ini_f, fim_f = inicio + (fim - inicio) / 2, fim
            rng_f = random.Random(semente * 100 + 10 * ti + k)  # sorteio próprio: fevereiro não altera o janeiro dos demais grupos
            for i, ev in enumerate(escolhidos_f):
                r = rng_f.random()
                erro = "conta" if r < perf["conta"] else "valor" if r < perf["conta"] + perf["valor"] else None
                quando = ini_f + (fim_f - ini_f) * (i / max(1, len(escolhidos_f) - 1))
                autor = a1.matricula if (perf.get("sozinho") or i % 2 == 0) else a2.matricula
                _lancar(db, d, por_f[ev], autor, quando, erro, rng_f)
            ac.ultimo_acesso = max(ac.ultimo_acesso or fim_f, fim_f)
        grupos.append((d, perf, a1, a2))
    db.flush()

    # notas: propostas para os enviados; homologadas onde o perfil pede
    linhas = analytics.propor_notas(db, t.id)
    for l in linhas:
        perf = PERFIS[l["d"].numero - 1]
        if perf["homologar"] and l["n"].nota_sistema is not None:
            l["n"].ajuste = 0.5 if l["m"].discente_id == grupos[l["d"].numero - 1][2].id else 0.0
            l["n"].observacao = "Participação ativa nas aulas de laboratório" if l["n"].ajuste else None
            l["n"].homologada, l["n"].homologada_em, l["n"].homologada_por = True, agora, cfg["login"]

    # acessos da turma: professor e um aluno (grupo 03, em andamento)
    professor = {"login": cfg["login"], "turma": cfg["codigo"], "nome": cfg["docente"],
                 "senha": _usuario(db, cfg["login"], f"{cfg['docente']} (demonstração)", "professor", docente_id=doc.id)}
    d3, _, a5, _ = grupos[2]
    senha_aluno = acesso.senha_provisoria()
    u = Usuario(login=a5.matricula, nome=a5.nome, senha_hash=acesso.gerar_hash(senha_aluno), discente_id=a5.id)
    u.perfis.append(UsuarioPerfil(perfil="aluno"))
    db.add(u)
    db.flush()
    aluno = {"login": a5.matricula, "senha": senha_aluno, "grupo": d3.rotulo, "turma": cfg["codigo"]}
    return {"turma_id": t.id, "professor": professor, "aluno": aluno, "grupos": len(grupos), "alunos": len(alunos)}


def main() -> None:
    from .db import Base, SessionLocal, engine
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        normas.semear(db)
        r = criar(db)
        acesso.registrar(db, None, "/admin/demonstracao", "Turmas de demonstração recriadas (servidor)", login="servidor")
    print(f"Turmas de demonstração: {', '.join(t['codigo'] + ' (' + t['docente'] + ')' for t in r['turmas'])}; "
          f"{r['grupos']} grupos, {r['alunos']} alunos fictícios.")
    c = r["credenciais"]
    print(f"  visitante  login: {c['visitante']['login']:16s} senha: {c['visitante']['senha']}")
    for p in c["professores"]:
        print(f"  professor  login: {p['login']:16s} senha: {p['senha']}  ({p['turma']})")
    for a in c["alunos"]:
        print(f"  aluno      login: {a['login']:16s} senha: {a['senha']}  ({a['turma']}, {a['grupo']})")
    print("Equipe entra em /entrar; o aluno em /aluno.")


if __name__ == "__main__":
    main()
