"""Casos de uso das skins. Toda regra de "pode / nao pode" passa por aqui."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..dominio.erros import BackupNecessario, NadaParaDesfazer, SkinNaoEncontrada
from ..dominio.preferencias import Preferencias
from ..dominio.skin import Origem, Skin
from .portas import Desktop, Estado, Migrador, Progresso, RepositorioSkins


def _nada(*_a, **_k):
    pass


def _agora():
    return datetime.now().replace(microsecond=0)


@dataclass
class Resultado:
    skin: Optional[Skin]
    avisos: list = field(default_factory=list)


class ServicoSkins:
    def __init__(self, repo: RepositorioSkins, desktop: Desktop, estado: Estado,
                 usuario: str, migrador: Optional[Migrador] = None):
        self.repo, self.desktop, self.estado = repo, desktop, estado
        self.usuario = usuario or "Você"
        self.migrador = migrador

    def listar(self, busca: str = "") -> list[Skin]:
        skins = self.repo.listar()
        for s in skins:
            if not s.incluida and not s.autor:
                s.autor = self.usuario
        return [s for s in skins if s.combina(busca)]

    def incluidas(self, busca: str = "") -> list[Skin]:
        """Oficiais: a padrao primeiro, depois por nome."""
        return sorted((s for s in self.listar(busca) if s.incluida),
                      key=lambda s: (not s.padrao, s.nome.lower()))

    def do_usuario(self, busca: str = "") -> list[Skin]:
        """Skins do usuario: as mais recentes primeiro."""
        def recente(s):
            d = s.atualizado_em or s.criado_em
            return -d.timestamp() if d else 0
        return sorted((s for s in self.listar(busca) if not s.incluida), key=recente)

    def obter(self, id_ou_nome: str) -> Skin:
        for s in self.listar():
            if id_ou_nome in (s.id, s.nome):
                return s
        raise SkinNaoEncontrada(f"Skin “{id_ou_nome}” não encontrada.")

    def ativa(self) -> Optional[Skin]:
        """A skin aplicada agora, se o visual na tela ainda bate com ela."""
        skins = self.listar()
        sid = self.estado.skin_ativa()
        for s in skins:
            if s.id == sid:
                return s if self.desktop.corresponde(s) else None
        return next((s for s in skins if self.desktop.corresponde(s)), None)

    def precisa_backup(self) -> bool:
        """Primeira troca: o usuario ainda nao tem nenhuma skin propria e o visual
        da tela nao e nenhuma skin conhecida. Sem backup, ele nao teria como voltar."""
        return not self.do_usuario() and self.ativa() is None

    def pode_desfazer(self) -> bool:
        return self.repo.desfazer_disponivel() is not None

    def pasta_minhas_skins(self) -> Path:
        return self.repo.usuario

    def preferencias(self) -> Preferencias:
        return self.estado.preferencias()

    def gravar_preferencias(self, prefs: Preferencias) -> None:
        self.estado.gravar_preferencias(prefs)

    def aplicar(self, skin: Skin, prefs: Optional[Preferencias] = None,
                progresso: Progresso = _nada) -> Resultado:
        self.desktop.verificar()
        if self.precisa_backup():
            raise BackupNecessario(
                "Antes da primeira troca, salve o visual atual como uma skin. "
                "Assim você sempre consegue voltar para ele.")
        prefs = prefs or self.estado.preferencias()
        self._guardar_desfazer(progresso)
        avisos = self.desktop.aplicar(skin, prefs, progresso)
        self.estado.definir_ativa(skin.id)
        return Resultado(skin, avisos)

    def desfazer(self, prefs: Optional[Preferencias] = None, progresso: Progresso = _nada) -> Resultado:
        self.desktop.verificar()
        if not self.pode_desfazer():
            raise NadaParaDesfazer("Não há troca de visual para desfazer.")
        prefs = prefs or self.estado.preferencias()
        with self.repo.desfazer_temporario() as anterior:
            estava_ativa = anterior.extras.get("estava_ativa")
            self._guardar_desfazer(progresso)
            avisos = self.desktop.aplicar(anterior, prefs, progresso)
        self.estado.definir_ativa(estava_ativa)
        return Resultado(None, avisos)

    def _guardar_desfazer(self, progresso):
        progresso("Guardando o visual atual para poder desfazer", 0.05)
        self.repo.gravar_desfazer(lambda pasta: self.desktop.capturar(pasta, leve=True),
                                  self.estado.skin_ativa())

    def salvar_atual(self, nome: str, descricao: str = "", capa: Optional[Path] = None,
                     progresso: Progresso = _nada) -> Skin:
        self.desktop.verificar()
        agora = _agora()
        skin = Skin(id=self.repo.novo_id(nome), nome=nome.strip(), origem=Origem.USUARIO,
                    descricao=descricao.strip(), autor=self.usuario, criado_em=agora,
                    atualizado_em=agora)
        skin = self.repo.gravar(skin, self._capturar_em(skin, progresso), capa)
        self.estado.definir_ativa(skin.id)
        return skin

    def duplicar(self, skin: Skin, nome: str, descricao: Optional[str] = None) -> Skin:
        agora = _agora()
        nova = Skin(id=self.repo.novo_id(nome), nome=nome.strip(), origem=Origem.USUARIO,
                    descricao=skin.descricao if descricao is None else descricao.strip(),
                    autor=self.usuario, criado_em=agora, atualizado_em=agora, dock=skin.dock,
                    baseada_em=skin.nome, extras=dict(skin.extras))
        return self.repo.copiar(skin, nova)

    def importar(self, caminho: Path) -> Skin:
        return self.repo.importar(Path(caminho), self.usuario)

    def migrar_legado(self) -> list[Skin]:
        return list(self.migrador.migrar()) if self.migrador else []

    def atualizar_com_atual(self, skin: Skin, capa: Optional[Path] = None,
                            progresso: Progresso = _nada) -> Skin:
        skin.exigir_editavel("atualizada")
        self.desktop.verificar()
        skin.atualizado_em = _agora()
        return self.repo.gravar(skin, self._capturar_em(skin, progresso), capa)

    def editar(self, skin: Skin, nome: str, descricao: str) -> Skin:
        skin.exigir_editavel("renomeada")
        skin.nome, skin.descricao = nome.strip(), descricao.strip()
        return self.repo.gravar(skin)

    def trocar_capa(self, skin: Skin, imagem_png: Path) -> None:
        skin.exigir_editavel("ter a capa trocada")
        self.repo.definir_capa(skin, imagem_png)

    def excluir(self, skin: Skin) -> None:
        skin.exigir_editavel("excluída")
        self.repo.excluir(skin)
        if self.estado.skin_ativa() == skin.id:
            self.estado.definir_ativa(None)

    def vincular(self, skin: Skin, **extras) -> Skin:
        """Guarda de onde a skin veio / para onde foi (galeria, nuvem)."""
        skin.exigir_editavel("alterada")
        for k, v in extras.items():
            if v is None:
                skin.extras.pop(k, None)
            else:
                skin.extras[k] = v
        return self.repo.gravar(skin)

    def exportar(self, skin: Skin, arquivo: str) -> str:
        return self.repo.exportar(skin, arquivo)

    def restaurar_tela_login(self) -> None:
        self.desktop.restaurar_tela_login()

    def _capturar_em(self, skin, progresso):
        def preencher(pasta):
            skin.dock = self.desktop.capturar(pasta, progresso=progresso)
        return preencher


