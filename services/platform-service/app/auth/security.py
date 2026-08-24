"""Primitivas de criptografia usadas pelo modulo de auth — sem acesso a
banco, sem regra de negocio, so as operacoes de hash em si. Separado pra
poder ser importado por outros modulos (ex.: app/identity/service.py precisa
de hash_token pra convites) sem puxar o resto da logica de auth junto."""
import hashlib
import bcrypt

EMAIL_REGEX = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'


def hash_password(password: str) -> str:
    """bcrypt com salt aleatorio embutido no proprio hash resultante — nao
    precisa guardar o salt em coluna separada."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Compara a senha digitada no login com o hash salvo — bcrypt.checkpw
    extrai o salt do proprio hash automaticamente."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_token(token: str) -> str:
    """sha256 usado tanto pra tokens de reset de senha quanto pra tokens de
    convite — nunca guardamos o valor puro no banco, so o hash."""
    return hashlib.sha256(token.encode()).hexdigest()
