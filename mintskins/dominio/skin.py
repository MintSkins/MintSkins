"""Entidade Skin e suas regras de negocio."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from .erros import SkinSomenteLeitura

AUTOR_MINTSKINS = "MintSkins"
ID_PADRAO = "macos"
EXTENSAO = ".mintskins"
EXTENSOES_ACEITAS = (EXTENSAO, ".mintskin")   # .mintskin: arquivos exportados antes do novo nome


class Origem(str, Enum):
    MINTSKINS = "mintskins"
    USUARIO = "usuario"


@dataclass
class Skin:
    id: str
    nome: str
    origem: Origem
    pasta: Optional[Path] = None
    descricao: str = ""
    autor: str = ""
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None
    dock: bool = False
    baseada_em: str = ""
    extras: dict = field(default_factory=dict)

    @property
    def incluida(self) -> bool:
        return self.origem is Origem.MINTSKINS

    @property
    def editavel(self) -> bool:
        return not self.incluida

    @property
    def padrao(self) -> bool:
        return self.incluida and self.id == ID_PADRAO

    @property
    def responsavel(self) -> str:
        return AUTOR_MINTSKINS if self.incluida else (self.autor or "Você")

    @property
    def foi_atualizada(self) -> bool:
        return bool(self.atualizado_em and self.criado_em and self.atualizado_em != self.criado_em)

    def exigir_editavel(self, acao: str = "alterada") -> None:
        if not self.editavel:
            raise SkinSomenteLeitura(
                f"“{self.nome}” é uma skin oficial do MintSkins e não pode ser {acao}. "
                "Use Duplicar para criar uma cópia sua.")

    def combina(self, busca: str) -> bool:
        q = (busca or "").strip().lower()
        return not q or any(q in t.lower() for t in (self.nome, self.descricao, self.responsavel))
