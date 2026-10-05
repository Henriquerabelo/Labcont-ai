"""Leitura dos relatórios em PDF exportados do SIGAA/UFC.

Dois formatos são suportados:

* "Consulta Geral de Turmas"  -> disciplinas, turmas e docentes
* "Lista de participantes"    -> turma, docentes e discentes (Turma Virtual)

As funções devolvem estruturas simples (dicts/listas) que são exibidas em
uma prévia antes de qualquer gravação no banco de dados.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import BinaryIO

import pdfplumber

# --------------------------------------------------------------------------
# Estruturas de dados
# --------------------------------------------------------------------------


@dataclass
class DocenteImport:
    nome: str
    email: str | None = None
    departamento: str | None = None
    formacao: str | None = None
    carga_horaria: int | None = None


@dataclass
class DiscenteImport:
    nome: str
    matricula: str
    email: str | None = None
    curso: str | None = None
    turno: str | None = None
    situacao: str = "ATIVO"


@dataclass
class TurmaImport:
    disciplina_codigo: str
    disciplina_nome: str
    periodo: str
    codigo: str
    tipo: str | None = None
    situacao: str | None = None
    horario: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    local: str | None = None
    matriculados: int | None = None
    capacidade: int | None = None
    docentes: list[DocenteImport] = field(default_factory=list)
    discentes: list[DiscenteImport] = field(default_factory=list)


@dataclass
class ResultadoImportacao:
    tipo: str  # "turmas" | "participantes"
    turmas: list[TurmaImport]
    avisos: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

RE_DISC = re.compile(r"^([A-Z]{2,4}\d{3,4})\s*-\s*(.+?)\s*(\((GRADUAÇÃO|PÓS-GRADUAÇÃO|[A-ZÇÃÕÉ\- ]+)\))?$")
RE_PERIODO = re.compile(r"^\d{4}\.\d$")
RE_DOCENTE_CH = re.compile(r"(.+?)\s*\((\d+)h\)")
RE_DATAS = re.compile(r"\((\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\)")
RE_MATCAP = re.compile(r"(\d+)\s*/\s*(\d+)")
RE_RODAPE = re.compile(r"^(https?://|\d+/\d+$|SIGAA \||\d{2}/\d{2}/\d{4}, \d{2}:\d{2})")


def _limpa(texto: str | None) -> str | None:
    if texto is None:
        return None
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto or None


def _data_iso(d: str | None) -> str | None:
    if not d:
        return None
    dia, mes, ano = d.split("/")
    return f"{ano}-{mes}-{dia}"


def detectar_tipo(texto_primeira_pagina: str) -> str | None:
    t = texto_primeira_pagina
    if "Lista de participantes" in t:
        return "participantes"
    if "Consulta Geral de Turmas" in t or "Turmas Encontradas" in t:
        return "turmas"
    return None


def ler_pdf(arquivo: str | BinaryIO) -> ResultadoImportacao:
    """Detecta o tipo de relatório e delega ao leitor correspondente."""
    with pdfplumber.open(arquivo) as pdf:
        primeira = pdf.pages[0].extract_text() or ""
        tipo = detectar_tipo(primeira)
        if tipo == "participantes":
            return _ler_participantes(pdf)
        if tipo == "turmas":
            return _ler_turmas(pdf)
    raise ValueError(
        "Formato de PDF não reconhecido. Use a 'Consulta Geral de Turmas' ou a "
        "'Lista de participantes' (Turma Virtual) exportadas do SIGAA."
    )


# --------------------------------------------------------------------------
# Consulta Geral de Turmas
# --------------------------------------------------------------------------

# Limites horizontais das colunas do relatório (em pontos PDF, página A4).
COLS = {
    "periodo": (0, 80),
    "turma": (80, 110),
    "docente": (110, 316),
    "tipo": (316, 350),
    "situacao": (350, 393),
    "horario": (393, 447),
    "local": (447, 503),
    "matcap": (503, 10_000),
}
CABECALHO = {"Ano", "Período", "Docente(s)", "Tipo", "Situação", "Horário", "Local", "Mat./Cap."}


def _coluna(x0: float) -> str:
    for nome, (a, b) in COLS.items():
        if a <= x0 < b:
            return nome
    return "matcap"


def _ler_turmas(pdf) -> ResultadoImportacao:
    palavras: list[dict] = []
    deslocamento = 0.0
    inicio_resultados = None
    for n, pg in enumerate(pdf.pages):
        h = pg.height
        for w in pg.extract_words(keep_blank_chars=False, use_text_flow=False):
            if n == 0 and inicio_resultados is None and w["text"] == "Encontradas":
                inicio_resultados = w["top"]
            palavras.append({**w, "y": deslocamento + w["top"], "pg": n, "h": h})
        deslocamento += h
    if inicio_resultados is None:
        raise ValueError("Não encontrei o bloco 'Turmas Encontradas' no PDF.")

    # remove o formulário de busca (página 1), cabeçalhos e rodapés
    linhas_rodape: set[tuple[int, int]] = set()
    por_linha: dict[tuple[int, int], list[dict]] = {}
    for w in palavras:
        por_linha.setdefault((w["pg"], round(w["top"])), []).append(w)
    for chave, ws in por_linha.items():
        texto = " ".join(x["text"] for x in sorted(ws, key=lambda x: x["x0"]))
        if RE_RODAPE.match(texto) or "SIGAA - UFC" in texto or texto.startswith("https://"):
            linhas_rodape.add(chave)
    uteis = []
    for w in palavras:
        if w["pg"] == 0 and w["top"] <= inicio_resultados + 2:
            continue
        if (w["pg"], round(w["top"])) in linhas_rodape:
            continue
        if w["text"] in CABECALHO:
            continue
        if w["text"].startswith("https://") or re.fullmatch(r"\d+/\d+", w["text"]) and w["top"] > w["h"] - 40:
            continue
        uteis.append(w)
    uteis.sort(key=lambda w: (w["y"], w["x0"]))

    # cabeçalhos de disciplina: linha que começa com código (ex.: EH0012) em x < 80
    linhas: dict[float, list[dict]] = {}
    for w in uteis:
        linhas.setdefault(round(w["y"]), []).append(w)
    disciplinas: list[tuple[float, str, str]] = []  # (y, codigo, nome)
    for y, ws in sorted(linhas.items()):
        ws = sorted(ws, key=lambda w: w["x0"])
        if ws and ws[0]["x0"] < 80 and re.fullmatch(r"[A-Z]{2,4}\d{3,4}", ws[0]["text"]):
            texto = " ".join(w["text"] for w in ws)
            m = RE_DISC.match(texto)
            if m:
                disciplinas.append((y, m.group(1), _limpa(m.group(2))))
    y_disc = [y for y, _, _ in disciplinas]

    def em_disc(y: float) -> bool:
        return any(abs(y - yd) <= 2.5 for yd in y_disc)

    # Células da coluna "Horário": podem atravessar a quebra de página, por isso
    # são montadas em sequência e fechadas no fim do período "(dd/mm/aaaa - dd/mm/aaaa)".
    celulas_horario: list[list[dict]] = []
    atual_h: list[dict] = []
    for w in uteis:
        if _coluna(w["x0"]) != "horario" or em_disc(w["y"]):
            continue
        atual_h.append(w)
        if re.search(r"\d{2}/\d{2}/\d{4}\)$", w["text"]):
            celulas_horario.append(atual_h)
            atual_h = []
    if atual_h:
        celulas_horario.append(atual_h)

    ancoras = [w for w in uteis if w["x0"] < 80 and RE_PERIODO.match(w["text"])]
    turmas: list[TurmaImport] = []
    avisos: list[str] = []
    for i, a in enumerate(ancoras):
        y = a["y"]
        disc = [d for d in disciplinas if d[0] < y]
        if not disc:
            avisos.append(f"Turma sem disciplina identificada (y={y:.0f}).")
            continue
        y_disc_atual, cod, nome = disc[-1]
        prox_disc = min([d[0] for d in disciplinas if d[0] > y], default=float("inf"))
        ant = ancoras[i - 1]["y"] if i > 0 else -1e9
        prox = ancoras[i + 1]["y"] if i + 1 < len(ancoras) else 1e12
        topo = max((ant + y) / 2, y_disc_atual + 3)
        base = min((y + prox) / 2, prox_disc - 3)
        cel: dict[str, list[dict]] = {k: [] for k in COLS}
        for w in uteis:
            if topo <= w["y"] <= base and not em_disc(w["y"]):
                cel[_coluna(w["x0"])].append(w)
        cel["horario"] = [w for c in celulas_horario if topo <= c[0]["y"] <= base for w in c]
        txt = {k: _limpa(" ".join(x["text"] for x in sorted(v, key=lambda x: (x["y"], x["x0"])))) for k, v in cel.items()}

        codigo_turma = _limpa((txt["turma"] or "").replace("Turma", "")) or "01"
        horario_txt = txt["horario"] or ""
        datas = RE_DATAS.search(horario_txt)
        horario = _limpa(RE_DATAS.sub("", horario_txt))
        if horario:
            horario = re.sub(r"(\d{2}:\d{2})- (\d{2}:\d{2})", r"\1-\2", horario)
        matcap = RE_MATCAP.search(txt["matcap"] or "")
        docentes = [
            DocenteImport(nome=re.sub(r"^e\s+", "", _limpa(m.group(1))), carga_horaria=int(m.group(2)))
            for m in RE_DOCENTE_CH.finditer(txt["docente"] or "")
        ]
        if not docentes and txt["docente"]:
            docentes = [DocenteImport(nome=txt["docente"])]
        turmas.append(
            TurmaImport(
                disciplina_codigo=cod,
                disciplina_nome=nome,
                periodo=a["text"],
                codigo=codigo_turma,
                tipo=txt["tipo"],
                situacao=txt["situacao"],
                horario=horario,
                data_inicio=_data_iso(datas.group(1)) if datas else None,
                data_fim=_data_iso(datas.group(2)) if datas else None,
                local=txt["local"],
                matriculados=int(matcap.group(1)) if matcap else None,
                capacidade=int(matcap.group(2)) if matcap else None,
                docentes=docentes,
            )
        )
    m = re.search(r"Turmas Encontradas \((\d+)\)", pdf.pages[0].extract_text() or "")
    if m and int(m.group(1)) != len(turmas):
        avisos.append(f"O relatório informa {m.group(1)} turmas; foram lidas {len(turmas)}.")
    return ResultadoImportacao(tipo="turmas", turmas=turmas, avisos=avisos)


# --------------------------------------------------------------------------
# Lista de participantes (Turma Virtual)
# --------------------------------------------------------------------------

RE_CAB_TURMA = re.compile(
    r"([A-Z]{2}\d{4})\s*-\s*(.+?)\s*-\s*Turma:\s*(\S+)\s*\((\d{4}\.\d)\)\s*-?\s*([A-ZÇÃ]+)?"
)


def _linhas_coluna(pg, x0: float, x1: float, y0: float) -> list[str]:
    area = pg.crop((x0, y0, x1, pg.height))
    texto = area.extract_text() or ""
    out = []
    for ln in texto.splitlines():
        ln = ln.strip()
        if not ln or RE_RODAPE.match(ln) or ln.startswith("https://") or "SIGAA" in ln:
            continue
        out.append(ln)
    return out


def _blocos_discentes(linhas: list[str]) -> list[DiscenteImport]:
    """Cada discente ocupa: NOME (1-2 linhas), Curso, (TURNO), Matrícula, E-mail, Turma."""
    res: list[DiscenteImport] = []
    nome: list[str] = []
    atual: dict | None = None
    campo_pendente = None
    for ln in linhas:
        if ln.startswith("Curso:"):
            atual = {"nome": " ".join(nome), "curso": ln[6:].strip()}
            nome = []
            campo_pendente = "curso"
            continue
        if atual is None:
            nome.append(ln)
            continue
        if ln.startswith("Matrícula:"):
            atual["matricula"] = ln.split(":", 1)[1].strip()
            campo_pendente = None
        elif ln.startswith("E-mail:"):
            v = ln.split(":", 1)[1].strip()
            atual["email"] = v or None
            campo_pendente = None if v else "email"
        elif ln.startswith("Turma:"):
            atual["turma"] = ln.split(":", 1)[1].strip()
            res.append(_monta_discente(atual))
            atual = None
            campo_pendente = None
        elif campo_pendente == "curso":
            atual["curso"] = f"{atual['curso']} {ln}"
        elif campo_pendente == "email":
            atual["email"] = ln.strip()
            campo_pendente = None
    return res


def _monta_discente(d: dict) -> DiscenteImport:
    nome = d["nome"]
    situacao = "ATIVO"
    m = re.search(r"\((TRANCADO|CANCELADO|DESISTENTE|[A-Z]+)\)\s*$", nome)
    if m:
        situacao = m.group(1)
        nome = nome[: m.start()].strip()
    curso = d.get("curso") or ""
    turno = None
    mt = re.search(r"\((DIURNO|NOTURNO|INTEGRAL|MATUTINO|VESPERTINO)\)", curso)
    if mt:
        turno = mt.group(1)
        curso = curso[: mt.start()].strip()
    return DiscenteImport(
        nome=_limpa(nome),
        matricula=d.get("matricula", "").strip(),
        email=(d.get("email") or None),
        curso=_limpa(curso),
        turno=turno,
        situacao=situacao,
    )


def _ler_participantes(pdf) -> ResultadoImportacao:
    avisos: list[str] = []
    p0 = pdf.pages[0]
    texto0 = p0.extract_text() or ""
    cab = RE_CAB_TURMA.search(re.sub(r"\s+", " ", texto0))
    if not cab:
        raise ValueError("Não encontrei o cabeçalho 'CÓDIGO - DISCIPLINA - Turma: NN (AAAA.P)'.")
    cod, nome_disc, _turma_num, periodo, situacao = cab.groups()

    # Docentes: bloco entre "Professores (n)" e "Alunos (n)" do texto completo
    docentes: list[DocenteImport] = []
    bloco = texto0.split("Alunos (")[0].split("Professores (", 1)[-1]
    linhas_prof = [ln.strip() for ln in bloco.splitlines()[1:] if ln.strip()]
    atual: DocenteImport | None = None
    turma_codigo = None
    for ln in linhas_prof:
        if ln.startswith("Departamento:"):
            if atual:
                atual.departamento = ln.split(":", 1)[1].strip()
        elif ln.startswith("Formação:"):
            if atual:
                atual.formacao = ln.split(":", 1)[1].strip()
        elif ln.startswith("E-mail:"):
            if atual:
                atual.email = ln.split(":", 1)[1].strip() or None
        elif ln.startswith("Turma(s):"):
            turma_codigo = turma_codigo or ln.split(":", 1)[1].strip().split(",")[0].strip()
        else:
            atual = DocenteImport(nome=_limpa(ln))
            docentes.append(atual)

    # Discentes: relatório em duas colunas. Um bloco pode continuar na mesma
    # coluna da página seguinte, então cada coluna é lida como um fluxo contínuo.
    fluxo_esq: list[str] = []
    fluxo_dir: list[str] = []
    for n, pg in enumerate(pdf.pages):
        y0 = 0
        if n == 0:
            alvo = [w for w in pg.extract_words() if w["text"] == "Alunos"]
            if not alvo:
                continue
            y0 = alvo[0]["bottom"] + 2
        meio = pg.width / 2 - 5
        fluxo_esq += _linhas_coluna(pg, 0, meio, y0)
        fluxo_dir += _linhas_coluna(pg, meio, pg.width, y0)
    discentes: list[DiscenteImport] = _blocos_discentes(fluxo_esq) + _blocos_discentes(fluxo_dir)

    m = re.search(r"Alunos \((\d+)\)", texto0)
    if m and int(m.group(1)) != len(discentes):
        avisos.append(f"O relatório informa {m.group(1)} alunos; foram lidos {len(discentes)}.")
    for d in discentes:
        if not d.matricula:
            avisos.append(f"Discente sem matrícula: {d.nome}")
    turma = TurmaImport(
        disciplina_codigo=cod,
        disciplina_nome=_limpa(nome_disc),
        periodo=periodo,
        codigo=turma_codigo or _turma_num,
        situacao=situacao,
        docentes=docentes,
        discentes=discentes,
    )
    return ResultadoImportacao(tipo="participantes", turmas=[turma], avisos=avisos)
