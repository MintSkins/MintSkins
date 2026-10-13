"""Migracao do antigo mac.sh: o backup do Mint original vira skin."""
import os
import shutil
from datetime import datetime
from pathlib import Path

from ..dominio.skin import Origem, Skin
from .cinnamon import _habilitada, _ler_desktop, generalizar_spices
from .perfil import caminho_de_uri, generalizar

MARCA = "migrado_mac_sh"


class MigradorMacSh:
    def __init__(self, repo, estado, usuario, backup, flag_ativo, id_mac="macos"):
        self.repo, self.estado, self.usuario = repo, estado, usuario
        self.backup, self.flag_ativo, self.id_mac = Path(backup), Path(flag_ativo), id_mac

    def migrar(self):
        """Roda uma vez por maquina."""
        if self.estado.marcado(MARCA):
            return []
        novas = []
        if (self.backup / "perfil.conf").is_file():
            novas.append(self._importar_backup())
        if self.flag_ativo.exists() and not self.estado.skin_ativa():
            self.estado.definir_ativa(self.id_mac)
        self.estado.marcar(MARCA, datetime.now().isoformat())
        return novas

    def _importar_backup(self, nome="Meu Mint original"):
        b = self.backup
        criado = datetime.now().replace(microsecond=0)
        try:
            criado = datetime.strptime((b / "criado_em").read_text().strip(), "%d/%m/%Y %H:%M")
        except (OSError, ValueError):
            pass
        skin = Skin(id=self.repo.novo_id(nome), nome=nome, origem=Origem.USUARIO,
                    descricao="Visual do Linux Mint antes do macOS (backup do mac.sh).",
                    autor=self.usuario, criado_em=criado, atualizado_em=criado,
                    dock=(b / "plank.desktop").is_file() and _habilitada(_ler_desktop(b / "plank.desktop")))

        def preencher(tmp):
            (tmp / "arquivos").mkdir()
            (tmp / "perfil.conf").write_text(
                generalizar((b / "perfil.conf").read_text(encoding="utf-8")), encoding="utf-8")
            if (b / "spices").is_dir():
                shutil.copytree(b / "spices", tmp / "spices", symlinks=True)
                generalizar_spices(tmp / "spices", tmp / "arquivos")
            if (b / "plank").is_dir():
                shutil.copytree(b / "plank", tmp / "plank", symlinks=True)
                for f in (tmp / "plank").rglob("*.dockitem"):
                    f.write_text(generalizar(f.read_text(encoding="utf-8", errors="ignore")),
                                 encoding="utf-8")
            conf = b / "papel_de_parede.conf"
            if conf.is_file():
                dados = dict(l.split("\t", 1) for l in conf.read_text(encoding="utf-8").splitlines()
                             if "\t" in l)
                fundo = caminho_de_uri(dados.get("picture-uri", ""))
                if os.path.isfile(fundo):
                    ext = os.path.splitext(fundo)[1] or ".jpg"
                    shutil.copy2(fundo, tmp / "arquivos" / f"papel_de_parede{ext}")
                    opc = dados.get("picture-options", "'zoom'")
                    (tmp / "papel_de_parede.conf").write_text(
                        f"arquivo\tpapel_de_parede{ext}\npicture-options\t{opc}\n", encoding="utf-8")
            if not any((tmp / "arquivos").iterdir()):
                (tmp / "arquivos").rmdir()

        return self.repo.gravar(skin, preencher)
