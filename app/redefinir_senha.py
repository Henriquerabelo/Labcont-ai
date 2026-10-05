"""Gera uma senha provisória para um usuário, direto no servidor (para quando o único administrador perde a senha).

Uso no VPS:  docker exec labcont-app python -m app.redefinir_senha admin
"""
import sys

from sqlalchemy import select

from . import acesso
from .db import SessionLocal


def main() -> None:
    if len(sys.argv) != 2:
        print("uso: python -m app.redefinir_senha <login>")
        sys.exit(1)
    with SessionLocal() as db:
        u = db.scalar(select(acesso.Usuario).where(acesso.Usuario.login == sys.argv[1].lower()))
        if not u:
            print("Usuário não encontrado.")
            sys.exit(1)
        senha = acesso.senha_provisoria()
        u.senha_hash, u.trocar_senha, u.ativo = acesso.gerar_hash(senha), True, True
        acesso.registrar(db, None, "/redefinir_senha", f"Senha provisória gerada no servidor para {u.login}", login="servidor")
        print(f"Senha provisória de {u.login}: {senha}  (troque no primeiro acesso)")


if __name__ == "__main__":
    main()
