"""Configurações lidas de variáveis de ambiente (arquivo .env opcional)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _carregar_env() -> None:
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()

# Fuso horário do sistema: horas gravadas e exibidas no horário de Brasília (UTC-3, sem horário de verão).
# O servidor (VPS/Docker) roda em UTC; sem isto, "agora" sairia 3 horas adiantado.
FUSO = os.getenv("APP_FUSO", "America/Fortaleza")


def _aplicar_fuso() -> None:
    if not hasattr(__import__("time"), "tzset"):  # Windows: já usa a hora local do computador
        return
    import time
    zona = Path("/usr/share/zoneinfo") / FUSO
    os.environ["TZ"] = FUSO if zona.exists() else "<-03>3"  # sem a base de fusos: UTC-3 fixo
    time.tzset()


_aplicar_fuso()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://labcont:labcont@localhost:5432/labcont"
)
APP_NOME = os.getenv("APP_NOME", "LABCONT-AI")
# Proteção opcional (HTTP Basic) para quando o protótipo for publicado.
# Deixe em branco no servidor local.
APP_USUARIO = os.getenv("APP_USUARIO", "")
APP_SENHA = os.getenv("APP_SENHA", "")
