"""Item da galeria: uma skin publicada (ou guardada) na nuvem."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .skin import AUTOR_MINTSKINS

ID_PERFIL_MINTSKINS = "mintskins"
PREFIXO_OFICIAL = "oficial:"


@dataclass
class ItemGaleria:
    id: str
    nome: str
    autor_id: str
    autor_nome: str
    descricao: str = ""
    publica: bool = True
    oficial: bool = False
    publicada_em: Optional[datetime] = None
    downloads: int = 0
    favoritos: int = 0
    tamanho: int = 0
    dock: bool = False
    pasta: Optional[Path] = None
    skin_local: str = ""
    favorito: bool = False
    extras: dict = field(default_factory=dict)

    @property
    def instalada(self) -> bool:
        return bool(self.skin_local)

    def combina(self, busca: str) -> bool:
        q = (busca or "").strip().lower()
        return not q or any(q in t.lower() for t in (self.nome, self.descricao, self.autor_nome))


def id_oficial(skin_id: str) -> str:
    return PREFIXO_OFICIAL + skin_id


def item_oficial(skin) -> ItemGaleria:
    return ItemGaleria(id=id_oficial(skin.id), nome=skin.nome, autor_id=ID_PERFIL_MINTSKINS,
                       autor_nome=AUTOR_MINTSKINS, descricao=skin.descricao, oficial=True,
                       publicada_em=skin.criado_em, dock=skin.dock, pasta=skin.pasta,
                       skin_local=skin.id)
