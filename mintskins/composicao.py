"""Raiz de composicao: o unico lugar que conhece todas as camadas."""
import os
import pwd
from dataclasses import dataclass

from .aplicacao.servico import ServicoSkins
from .aplicacao.servico_atualizacoes import ServicoAtualizacoes
from .aplicacao.servico_nuvem import ServicoNuvem
from .infra import caminhos
from .infra.atualizador import AtualizadorGitHub
from .infra.capas import GeradorCapas
from .infra.cinnamon import DesktopCinnamon
from .infra.estado import EstadoArquivo
from .infra.legado import MigradorMacSh
from .infra.nuvem_local import NuvemLocal
from .infra.repositorio import RepositorioArquivos


@dataclass
class Aplicativo:
    skins: ServicoSkins
    nuvem: ServicoNuvem
    atualizacoes: ServicoAtualizacoes
    capas: GeradorCapas


def nome_do_usuario():
    """Nome real da conta do sistema (campo GECOS), senao o login."""
    try:
        p = pwd.getpwuid(os.getuid())
        return p.pw_gecos.split(",")[0].strip() or p.pw_name
    except KeyError:
        return os.environ.get("USER", "")


def montar():
    caminhos.migrar_pastas_antigas()
    repo = RepositorioArquivos(caminhos.SKINS_USUARIO, caminhos.SKINS_MINTSKINS, caminhos.DESFAZER)
    estado = EstadoArquivo(caminhos.CONFIG)
    usuario = nome_do_usuario()
    migrador = MigradorMacSh(repo, estado, usuario, caminhos.MAC_SH_BACKUP, caminhos.MAC_SH_ATIVO)
    skins = ServicoSkins(repo, DesktopCinnamon(), estado, usuario, migrador)
    return Aplicativo(
        skins=skins,
        nuvem=ServicoNuvem(NuvemLocal(caminhos.NUVEM_LOCAL), estado, skins),
        atualizacoes=ServicoAtualizacoes(AtualizadorGitHub(), estado, caminhos.CACHE / "atualizacoes"),
        capas=GeradorCapas(caminhos.CACHE / "capas"),
    )
