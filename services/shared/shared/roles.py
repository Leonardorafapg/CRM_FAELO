"""UserRole vive aqui (nao em platform-service) porque crm-service e
conversation-service precisam checar nivel de permissao a partir do JWT sem
depender do banco/modelos do platform-service — o token ja carrega o role
como claim, cada servico so precisa saber comparar niveis."""
import enum


class UserRole(str, enum.Enum):
    owner     = "owner"
    admin     = "admin"
    attendant = "attendant"


ROLE_LEVEL = {
    UserRole.attendant: 0,
    UserRole.admin: 1,
    UserRole.owner: 2,
}
