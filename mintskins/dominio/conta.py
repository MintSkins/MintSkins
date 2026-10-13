"""Conta do usuario e perfil publico."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .erros import DadosInvalidos

SENHA_MINIMA = 8
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Conta:
    id: str
    nome: str
    email: str
    criada_em: Optional[datetime] = None

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
    nome, email = (nome or "").strip(), (email or "").strip().lower()
    if len(nome) < 2:
        raise DadosInvalidos("Informe seu nome.")
    if not _EMAIL.match(email):
        raise DadosInvalidos("Informe um e-mail válido.")
    if len(senha or "") < SENHA_MINIMA:
        raise DadosInvalidos(f"A senha precisa ter pelo menos {SENHA_MINIMA} caracteres.")
    return nome, email
