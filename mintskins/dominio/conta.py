"""Conta do usuario e perfil publico."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .erros import DadosInvalidos

SENHA_MINIMA = 8
BIO_MAXIMA = 160
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Conta:
    id: str
    nome: str
    email: str
    criada_em: Optional[datetime] = None
    bio: str = ""
    foto: Optional[str] = None      # caminho de uma imagem quadrada, ou None (mostra as iniciais)
    banner: Optional[str] = None    # imagem larga do topo do perfil
    localizacao: str = ""
    site: str = ""
    github: str = ""
    seguidores: int = 0
    seguindo: int = 0
    pagina: str = ""                # endereco do perfil no site

    @property
    def iniciais(self) -> str:
        return iniciais(self.nome)


@dataclass
class Perfil:
    id: str
    nome: str
    desde: Optional[datetime] = None
    oficial: bool = False
    itens: list = field(default_factory=list)
    bio: str = ""
    foto: Optional[str] = None
    banner: Optional[str] = None
    localizacao: str = ""
    site: str = ""
    github: str = ""
    seguidores: int = 0
    seguindo: int = 0
    pagina: str = ""

    @property
    def iniciais(self) -> str:
        return iniciais(self.nome)

    @property
    def downloads(self) -> int:
        return sum(i.downloads for i in self.itens)


def iniciais(nome: str) -> str:
    partes = [p for p in (nome or "?").split() if p]
    return ((partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")) if partes else "?").upper()


def validar_cadastro(nome: str, email: str, senha: str) -> tuple:
    nome, email, _bio = validar_perfil(nome, email)
    validar_senha(senha)
    return nome, email


def validar_perfil(nome: str, email: str, bio: str = "") -> tuple:
    nome, email = " ".join((nome or "").split()), (email or "").strip().lower()
    bio = (bio or "").strip()
    if len(nome) < 2:
        raise DadosInvalidos("Informe seu nome.")
    if len(nome) > 60:
        raise DadosInvalidos("O nome pode ter no máximo 60 caracteres.")
    if not _EMAIL.match(email):
        raise DadosInvalidos("Informe um e-mail válido.")
    if len(bio) > BIO_MAXIMA:
        raise DadosInvalidos(f"A bio pode ter no máximo {BIO_MAXIMA} caracteres.")
    return nome, email, bio


def validar_senha(senha: str) -> None:
    if len(senha or "") < SENHA_MINIMA:
        raise DadosInvalidos(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
