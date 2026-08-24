"""UserRole vive aqui (nao em platform-service) porque crm-service e
conversation-service precisam checar nivel de permissao a partir do JWT sem
depender do banco/modelos do platform-service — o token ja carrega o role
como claim, cada servico so precisa saber comparar niveis."""
import enum


# Os 3 papeis que um usuario pode ter dentro de um tenant. Guardado como string
# no banco (herda de str) pra ficar legivel direto na coluna, sem precisar
# decodificar um inteiro.
class UserRole(str, enum.Enum):
    owner     = "owner"      # dono da conta — acesso total, unico que pode criar outro owner
    admin     = "admin"      # acesso administrativo (config, conexoes, equipe) exceto criar owner
    attendant = "attendant"  # operacional: atender, mover lead, sem acesso a configuracao


# Mapa de role -> nivel numerico, usado por policy.py pra comparar "esse role
# tem PELO MENOS o nivel exigido?" (ex.: admin=1 >= attendant_minimo=0 -> passa).
ROLE_LEVEL = {
    UserRole.attendant: 0,
    UserRole.admin: 1,
    UserRole.owner: 2,
}
