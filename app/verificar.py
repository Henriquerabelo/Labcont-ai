"""Verifica a conexão com o PostgreSQL antes de iniciar o sistema.

Se o usuário ou o banco ainda não existirem, cria-os automaticamente usando a
senha de administrador informada em PG_ADMIN_SENHA no arquivo .env. Sem essa
senha, pergunta uma única vez (exceto no modo --auto, que nunca pergunta).

Uso: python -m app.verificar [--auto]
Códigos de saída: 0 = tudo certo | 1 = erro | 2 = PostgreSQL fora do ar
"""
from __future__ import annotations

import getpass
import os
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from .config import DATABASE_URL


def _conectar(url) -> None:
    with psycopg.connect(
        host=url.host or "localhost", port=url.port or 5432, user=url.username,
        password=url.password, dbname=url.database, connect_timeout=5,
    ):
        pass


def _criar_banco(url, auto: bool) -> bool:
    admin = os.getenv("PG_ADMIN_USUARIO") or "postgres"
    senha = os.getenv("PG_ADMIN_SENHA") or ""
    print("Criando o usuário e o banco do LABCONT-AI no PostgreSQL...")
    if not senha:
        if auto:
            print('Informe a senha do usuário "postgres" em PG_ADMIN_SENHA no arquivo .env e execute novamente.')
            return False
        senha = getpass.getpass(f'Digite a senha do usuário "{admin}" do PostgreSQL (só nesta primeira vez): ')
    try:
        with psycopg.connect(host=url.host or "localhost", port=url.port or 5432, user=admin,
                             password=senha, dbname="postgres", autocommit=True, connect_timeout=5) as c:
            existe = c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (url.username,)).fetchone()
            if not existe:
                c.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(url.username), sql.Literal(url.password)))
            for banco in (url.database, f"{url.database}_test"):
                if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (banco,)).fetchone():
                    c.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(banco), sql.Identifier(url.username)))
        print("Banco criado com sucesso.")
        return True
    except psycopg.OperationalError as e:
        print(f"\nNão foi possível entrar como {admin}: {e}")
        print("Confira a senha em PG_ADMIN_SENHA no arquivo .env.")
        return False


def main() -> int:
    auto = "--auto" in sys.argv
    url = make_url(DATABASE_URL)
    try:
        _conectar(url)
        print("PostgreSQL: conexão OK.")
        return 0
    except psycopg.OperationalError as e:
        msg = str(e).lower()

    if "connection refused" in msg or "could not connect" in msg or "timeout" in msg or "recusad" in msg or "não foi possível conectar" in msg:
        print()
        print(f"O PostgreSQL não está respondendo em {url.host}:{url.port or 5432}.")
        print("  Verifique em 'Serviços' do Windows se o serviço 'postgresql-x64-18' está em execução")
        print("  e com inicialização 'Automática'. Confira também a porta em DATABASE_URL, no arquivo .env.")
        return 2

    # Servidor no ar, mas usuário/banco ainda não existem (ou a senha não confere).
    print(f"\nO PostgreSQL respondeu: {msg.strip()}")
    if _criar_banco(url, auto):
        try:
            _conectar(url)
            print("PostgreSQL: conexão OK.")
            return 0
        except psycopg.OperationalError as e2:
            print(f"Ainda sem conexão: {e2}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
