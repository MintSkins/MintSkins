"""Caso de uso: descobrir e instalar versoes novas do MintSkins."""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..dominio.versao import NovaVersao
from .portas import Atualizacoes, Estado

INTERVALO = timedelta(hours=12)


class ServicoAtualizacoes:
    def __init__(self, fonte: Atualizacoes, estado: Estado, pasta_downloads: Path):
        self.fonte, self.estado, self.pasta = fonte, estado, Path(pasta_downloads)

    def verificar(self, forcar: bool = False) -> Optional[NovaVersao]:
        """Consulta no maximo a cada 12 h (ou sempre, se forcar). Versao ignorada nao volta."""
        if not forcar:
            ultima = self.estado.ler_valor("atualizacao_verificada_em")
            try:
                if ultima and datetime.now() - datetime.fromisoformat(ultima) < INTERVALO:
                    return None
            except ValueError:
                pass
        nova = self.fonte.ultima_versao()
        self.estado.gravar_valor("atualizacao_verificada_em", datetime.now().replace(microsecond=0).isoformat())
        if nova and not forcar and self.estado.ler_valor("versao_ignorada") == nova.versao:
            return None
        return nova

    def ignorar(self, nova: NovaVersao) -> None:
        self.estado.gravar_valor("versao_ignorada", nova.versao)

    def atualizar(self, nova: NovaVersao) -> None:
        pacote = self.fonte.baixar(nova, self.pasta)
        try:
            self.fonte.instalar(pacote)
        finally:
            pacote.unlink(missing_ok=True)
