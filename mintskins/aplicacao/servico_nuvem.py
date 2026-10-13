"""Casos de uso de conta, galeria e favoritos."""
from typing import Optional

from ..dominio.conta import Perfil
from ..dominio.erros import LoginNecessario, SemPermissao, SkinNaoEncontrada
from ..dominio.galeria import ID_PERFIL_MINTSKINS, PREFIXO_OFICIAL, ItemGaleria, item_oficial
from ..dominio.skin import AUTOR_MINTSKINS, Skin
from .portas import Estado, Nuvem
from .servico import ServicoSkins


class ServicoNuvem:
    def __init__(self, nuvem: Nuvem, estado: Estado, skins: ServicoSkins):
        self.nuvem, self.estado, self.skins = nuvem, estado, skins

    @property
    def token(self) -> Optional[str]:
        return self.estado.sessao()

    def conta(self):
        conta = self.nuvem.conta(self.token) if self.token else None
        if self.token and not conta:              # sessao expirada ou apagada
            self.estado.definir_sessao(None)
        return conta

    def criar_conta(self, nome, email, senha):
        token, conta = self.nuvem.criar_conta(nome, email, senha)
        self.estado.definir_sessao(token)
        return conta

    def entrar(self, email, senha):
        token, conta = self.nuvem.entrar(email, senha)
        self.estado.definir_sessao(token)
        return conta

    def sair(self):
        if self.token:
            self.nuvem.sair(self.token)
        self.estado.definir_sessao(None)

    def _exigir_login(self):
        if not self.conta():
            raise LoginNecessario("Entre na sua conta para continuar.")
        return self.token

    def galeria(self, filtro: str = "todas", busca: str = "") -> list[ItemGaleria]:
        oficiais = [item_oficial(s) for s in self.skins.incluidas()]
        comunidade = self.nuvem.galeria()
        itens = {"oficiais": oficiais, "comunidade": comunidade}.get(filtro, oficiais + comunidade)
        itens = self._enriquecer(itens)
        if filtro == "favoritas":
            itens = [i for i in itens if i.favorito]
        itens = [i for i in itens if i.combina(busca)]
        return sorted(itens, key=lambda i: (not i.oficial, -i.favoritos, -i.downloads, i.nome.lower()))

    def da_conta(self) -> list[ItemGaleria]:
        token = self._exigir_login()
        return self._enriquecer(self.nuvem.da_conta(token))

    def favoritas(self) -> list[ItemGaleria]:
        return self.galeria("favoritas") if self.conta() else []

    def item(self, item_id: str) -> ItemGaleria:
        if item_id.startswith(PREFIXO_OFICIAL):
            for s in self.skins.incluidas():
                if item_oficial(s).id == item_id:
                    return self._enriquecer([item_oficial(s)])[0]
            raise SkinNaoEncontrada("Skin não encontrada na galeria.")
        return self._enriquecer([self.nuvem.item(item_id, self.token)])[0]

    def perfil(self, autor_id: str) -> Optional[Perfil]:
        if autor_id == ID_PERFIL_MINTSKINS:
            return Perfil(id=ID_PERFIL_MINTSKINS, nome=AUTOR_MINTSKINS, oficial=True,
                          itens=self.galeria("oficiais"))
        perfil = self.nuvem.perfil(autor_id)
        if perfil:
            perfil.itens = self._enriquecer(perfil.itens)
        return perfil

    def _enriquecer(self, itens):
        """Marca favoritos da conta atual e o que ja esta instalado nesta maquina."""
        favs = self.nuvem.favoritos(self.token) if self.token else set()
        locais = {s.extras.get("galeria_id"): s.id for s in self.skins.do_usuario()}
        for i in itens:
            i.favorito = i.id in favs
            if i.oficial:
                i.favoritos = self.nuvem.contagem_favoritos(i.id)
            else:
                i.skin_local = locais.get(i.id, "")
        return itens

    def favoritar(self, item: ItemGaleria, favorito: bool) -> None:
        self.nuvem.favoritar(self._exigir_login(), item.id, favorito)

    def baixar(self, item: ItemGaleria) -> Skin:
        """Instala a skin da galeria em Minhas skins (ou devolve a ja instalada)."""
        if item.oficial or item.instalada:
            return self.skins.obter(item.skin_local)
        pasta = self.nuvem.baixar(item.id, self.token)
        skin = self.skins.importar(pasta)
        skin.autor = item.autor_nome
        return self.skins.vincular(skin, galeria_id=item.id, nuvem_id=None)

    def enviar(self, skin: Skin, publica: bool) -> ItemGaleria:
        """Guarda a skin na conta (privada) ou publica na galeria."""
        token = self._exigir_login()
        skin.exigir_editavel("enviada")
        anterior = skin.extras.get("nuvem_id")
        meta = {"nome": skin.nome, "descricao": skin.descricao, "dock": skin.dock}
        try:
            item = self.nuvem.enviar(token, skin.pasta, meta, publica, anterior)
        except (SkinNaoEncontrada, SemPermissao):
            item = self.nuvem.enviar(token, skin.pasta, meta, publica)
        self.skins.vincular(skin, nuvem_id=item.id, galeria_id=item.id)
        return item

    def definir_publica(self, item: ItemGaleria, publica: bool) -> None:
        self.nuvem.definir_publica(self._exigir_login(), item.id, publica)

    def remover(self, item: ItemGaleria) -> None:
        self.nuvem.remover(self._exigir_login(), item.id)
