"""Caso de uso: as notificacoes do sino, guardadas no estado do app."""
from typing import Optional

from ..dominio.notificacao import ACAO_ATUALIZACAO, Notificacao
from ..dominio.versao import mais_nova
from .portas import Estado

CHAVE = "notificacoes"
LIMITE = 30


class ServicoNotificacoes:
    def __init__(self, estado: Estado):
        self.estado = estado

    def _ler(self) -> list[Notificacao]:
        itens = []
        for d in self.estado.ler_valor(CHAVE) or []:
            try:
                itens.append(Notificacao.de_dict(d))
            except TypeError:
                pass
        return itens

    def _gravar(self, itens):
        itens = sorted(itens, key=lambda n: n.criada_em, reverse=True)[:LIMITE]
        self.estado.gravar_valor(CHAVE, [n.para_dict() for n in itens])

    def listar(self) -> list[Notificacao]:
        return sorted(self._ler(), key=lambda n: n.criada_em, reverse=True)

    def nao_lidas(self) -> int:
        return sum(not n.lida for n in self._ler())

    def adicionar(self, id: str, titulo: str, texto: str = "", tipo: str = "info",
                  acao: str = "") -> Optional[Notificacao]:
        """Nao repete: se a notificacao ja existe (lida ou nao), nada muda."""
        itens = self._ler()
        if any(n.id == id for n in itens):
            return None
        nova = Notificacao(id=id, titulo=titulo, texto=texto, tipo=tipo, acao=acao)
        self._gravar(itens + [nova])
        return nova

    def marcar_lidas(self) -> None:
        itens = self._ler()
        if any(not n.lida for n in itens):
            for n in itens:
                n.lida = True
            self._gravar(itens)

    def remover(self, id: str) -> None:
        self._gravar([n for n in self._ler() if n.id != id])

    def limpar(self) -> None:
        self._gravar([])

    def primeira_vez(self, chave: str) -> bool:
        """True so na primeira chamada com essa chave (avisos que aparecem uma vez)."""
        vistos = self.estado.ler_valor("avisos_vistos") or []
        if chave in vistos:
            return False
        self.estado.gravar_valor("avisos_vistos", vistos + [chave])
        return True

    def versao_disponivel(self, versao: str) -> Optional[Notificacao]:
        return self.adicionar(f"versao:{versao}", f"MintSkins {versao} disponível",
                              "Clique para ver as novidades e atualizar.", "atualizacao", ACAO_ATUALIZACAO)

    def ao_abrir(self, versao_atual: str) -> None:
        """Depois de uma atualizacao: tira os avisos velhos e avisa que deu certo."""
        anterior = self.estado.ler_valor("versao_aberta")
        if anterior == versao_atual:
            return
        self.estado.gravar_valor("versao_aberta", versao_atual)
        itens = [n for n in self._ler() if not n.id.startswith("pronta:")
                 and not (n.id.startswith("versao:") and not mais_nova(n.id[7:], versao_atual))]
        self._gravar(itens)
        if anterior and mais_nova(versao_atual, anterior):
            self.adicionar(f"instalada:{versao_atual}", f"Atualizado para o MintSkins {versao_atual}",
                           "Tudo pronto. Você já está usando a versão nova.", "sucesso")
