"""Casos de uso de conta, galeria e favoritos."""
from datetime import datetime
from typing import Optional

from ..dominio.conta import Perfil
from ..dominio.erros import LoginNecessario, SemConexao, SemPermissao, SkinNaoEncontrada
from ..dominio.galeria import ID_PERFIL_MINTSKINS, PREFIXO_OFICIAL, ItemGaleria, item_oficial
from ..dominio.skin import AUTOR_MINTSKINS, Skin
from .portas import Estado, Nuvem
from .servico import ServicoSkins


ORDENS = {
    "populares": lambda i: (not i.oficial, -i.favoritos, -i.downloads, i.nome.lower()),
    "recentes": lambda i: (-i.publicada_em.timestamp() if i.publicada_em else float("inf"), i.nome.lower()),
    "favoritadas": lambda i: (-i.favoritos, -i.downloads, i.nome.lower()),
}

# onde uma skin deste computador esta: so aqui, guardada na conta (privada) ou publicada na galeria
LOCAL, PRIVADA, PUBLICA = "local", "privada", "publica"


class ServicoNuvem:
    def __init__(self, nuvem: Nuvem, estado: Estado, skins: ServicoSkins, capas=None):
        self.nuvem, self.estado, self.skins, self.capas = nuvem, estado, skins, capas

    @property
    def site(self) -> str:
        return getattr(self.nuvem, "site", "https://mintskins.com")

    @property
    def token(self) -> Optional[str]:
        return self.estado.sessao()

    def conta(self):
        try:
            conta = self.nuvem.conta(self.token) if self.token else None
        except SemConexao:
            return None                           # sem internet: nao encerra a sessao
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

    def atualizar_perfil(self, nome, email, bio, links=None):
        """links: localizacao, site e github (o e-mail nao muda pelo app)."""
        return self.nuvem.atualizar_perfil(self._exigir_login(), nome, email, bio, links)

    def definir_foto(self, imagem_png):
        return self.nuvem.definir_foto(self._exigir_login(), imagem_png)

    def alterar_senha(self, atual, nova):
        self.nuvem.alterar_senha(self._exigir_login(), atual, nova)

    def _exigir_login(self):
        if not self.conta():
            raise LoginNecessario("Entre na sua conta para continuar.")
        return self.token

    def galeria(self, filtro: str = "todas", busca: str = "", ordem: str = "populares") -> list[ItemGaleria]:
        incluidas = self.skins.incluidas()
        oficiais = [item_oficial(s) for s in incluidas]
        # a conta oficial do site publica as mesmas skins que vem com o app: mostra so a do app
        ids_incluidas = {s.id for s in incluidas}
        comunidade = [i for i in self.nuvem.galeria()
                      if not (i.extras.get("oficial") and i.id in ids_incluidas)]
        itens = {"oficiais": oficiais, "comunidade": comunidade}.get(filtro, oficiais + comunidade)
        itens = self._enriquecer(itens)
        if filtro == "favoritas":
            itens = [i for i in itens if i.favorito]
        itens = [i for i in itens if i.combina(busca)]
        return sorted(itens, key=ORDENS.get(ordem, ORDENS["populares"]))

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
        if self.capas:
            meta["capa"] = str(self.capas.capa(skin))
        try:
            item = self.nuvem.enviar(token, skin.pasta, meta, publica, anterior)
        except (SkinNaoEncontrada, SemPermissao):
            item = self.nuvem.enviar(token, skin.pasta, meta, publica)
        self.skins.vincular(skin, nuvem_id=item.id, galeria_id=item.id,
                            enviada_em=datetime.now().replace(microsecond=0).isoformat())
        return item

    def situacao(self, skin: Skin, na_conta: dict) -> tuple:
        """(LOCAL | PRIVADA | PUBLICA, item da conta ou None). na_conta = {id: item} de da_conta()."""
        item = na_conta.get(skin.extras.get("nuvem_id") or "")
        if not item:
            return LOCAL, None
        return (PUBLICA if item.publica else PRIVADA), item

    @staticmethod
    def pendente(skin: Skin) -> bool:
        """A skin mudou neste computador depois do ultimo envio para a conta."""
        mudou, enviada = skin.extras.get("mudou_em"), skin.extras.get("enviada_em")
        return bool(skin.extras.get("nuvem_id") and mudou and (not enviada or mudou > enviada))

    def definir_publica(self, item: ItemGaleria, publica: bool) -> None:
        self.nuvem.definir_publica(self._exigir_login(), item.id, publica)

    def remover(self, item: ItemGaleria):
        """Pode devolver a pagina do site para confirmar a exclusao (codigo por e-mail)."""
        return self.nuvem.remover(self._exigir_login(), item.id)
