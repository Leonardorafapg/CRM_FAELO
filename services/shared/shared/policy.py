"""Autorizacao por role, centralizada — mesmo desenho do chat-api atual
(auth/policy.py), portado pra shared pra ser reusado pelos 3 servicos.

Rotas nunca devem checar `current_user["role"]` diretamente; usam
`require_role(...)` como dependency. `is_platform_admin` sempre passa,
independente do role.
"""
from fastapi import Depends, HTTPException, status

from shared.roles import UserRole, ROLE_LEVEL
from shared.auth_deps import get_current_user


def require_role(minimum: UserRole):
    """Factory de dependency: recebe o nivel MINIMO exigido e devolve uma
    dependency pronta pra usar em `Depends(...)`. Assim da pra escrever
    `Depends(require_role(UserRole.admin))` em qualquer rota sem repetir a
    logica de comparacao de nivel em cada uma."""
    def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        # Platform admin (super-admin cross-tenant) sempre passa, ignora a
        # checagem de role normal.
        if current_user.get("is_admin"):
            return current_user

        # Converte a string do claim "role" pro enum — se vier algo que nao e
        # um role valido (token corrompido/antigo), barra com 403 em vez de
        # deixar o KeyError do dict ROLE_LEVEL estourar como 500.
        raw_role = current_user.get("role")
        try:
            role = UserRole(raw_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Papel de usuario invalido para esta acao",
            )

        # Compara nivel numerico: precisa ser >= ao minimo exigido pela rota.
        if ROLE_LEVEL[role] < ROLE_LEVEL[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu papel nao tem permissao para esta acao",
            )
        return current_user

    return _dependency


# Atalhos prontos pros dois niveis mais usados — evita escrever
# require_role(UserRole.admin) toda vez.
require_admin = require_role(UserRole.admin)
require_owner = require_role(UserRole.owner)
