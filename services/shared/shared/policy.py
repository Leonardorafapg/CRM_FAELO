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
    def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("is_admin"):
            return current_user

        raw_role = current_user.get("role")
        try:
            role = UserRole(raw_role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Papel de usuario invalido para esta acao",
            )

        if ROLE_LEVEL[role] < ROLE_LEVEL[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu papel nao tem permissao para esta acao",
            )
        return current_user

    return _dependency


require_admin = require_role(UserRole.admin)
require_owner = require_role(UserRole.owner)
