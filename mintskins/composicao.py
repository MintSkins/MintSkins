"""Raiz de composicao: o unico lugar que conhece todas as camadas."""
import os
import pwd
from dataclasses import dataclass

from .aplicacao.servico import ServicoSkins
from .aplicacao.servico_atualizacoes import ServicoAtualizacoes
from .aplicacao.servico_notificacoes import ServicoNotificacoes
from .aplicacao.servico_nuvem import ServicoNuvem
from .infra import caminhos
from .infra.atualizador import AtualizadorGitHub
from .infra.capas import GeradorCapas
from .infra.cinnamon import DesktopCinnamon
from .infra.estado import EstadoArquivo
from .infra.inicio_automatico import InicioAutomatico
from .infra.legado import MigradorMacSh
from .infra.nuvem_site import NuvemSite
from .infra.repositorio import RepositorioArquivos


@dataclass
class Aplicativo:
    skins: ServicoSkins
    nuvem: ServicoNuvem
    atualizacoes: ServicoAtualizacoes
    notificacoes: ServicoNotificacoes
    inicio_automatico: InicioAutomatico
    capas: GeradorCapas


def nome_do_usuario():
    """Nome real da conta do sistema (campo GECOS), senao o login."""
    try:
        p = pwd.getpwuid(os.getuid())
        return p.pw_gecos.split(",")[0].strip() or p.pw_name
    except KeyError:
        return os.environ.get("USER", "")


def nome_do_computador():
    """Aparece no site, na lista de onde a conta esta logada."""
    try:
        return f"{nome_do_usuario()} em {os.uname().nodename}"[:60]
    except OSError:
        return "Linux Mint"


def montar():
    caminhos.migrar_pastas_antigas()
    repo = RepositorioArquivos(caminhos.SKINS_USUARIO, caminhos.SKINS_MINTSKINS, caminhos.DESFAZER)
    estado = EstadoArquivo(caminhos.CONFIG)
    usuario = nome_do_usuario()
    migrador = MigradorMacSh(repo, estado, usuario, caminhos.MAC_SH_BACKUP, caminhos.MAC_SH_ATIVO)
    skins = ServicoSkins(repo, DesktopCinnamon(), estado, usuario, migrador)
    capas = GeradorCapas(caminhos.CACHE / "capas")
    return Aplicativo(
        skins=skins,
        nuvem=ServicoNuvem(NuvemSite(caminhos.CACHE / "site", computador=nome_do_computador()), estado, skins, capas),
        atualizacoes=ServicoAtualizacoes(AtualizadorGitHub(), estado, caminhos.CACHE / "atualizacoes"),
        notificacoes=ServicoNotificacoes(estado),
        inicio_automatico=InicioAutomatico(),
        capas=capas,
    )
