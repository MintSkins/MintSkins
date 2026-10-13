"""Versoes do MintSkins (formato 1.2.3) e o aviso de versao nova."""
import re
from dataclasses import dataclass
from typing import Optional

from .erros import DadosInvalidos


def versao(texto: str) -> tuple:
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", (texto or "").strip())
    if not m:
        raise DadosInvalidos(f"Versão inválida: {texto!r}")
    return tuple(int(g or 0) for g in m.groups())


def mais_nova(candidata: str, atual: str) -> bool:
    try:
        return versao(candidata) > versao(atual)
    except DadosInvalidos:
        return False


@dataclass
class NovaVersao:
    versao: str
    notas: str = ""
    pagina: str = ""
    pacote_url: Optional[str] = None
    pacote_nome: str = ""
    sha256: Optional[str] = None
