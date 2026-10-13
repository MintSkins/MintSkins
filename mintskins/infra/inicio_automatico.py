"""Abrir o MintSkins junto com o sistema (arquivo em ~/.config/autostart)."""
from pathlib import Path

from .caminhos import AUTOSTART

ARQUIVO = "io.github.pabluoo.MintSkins.desktop"
CONTEUDO = """[Desktop Entry]
Type=Application
Name=MintSkins
Comment=Abre o MintSkins em segundo plano, no ícone perto do relógio
Icon=mintskins
TryExec=mintskins
Exec=mintskins --segundo-plano
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
"""


class InicioAutomatico:
    def __init__(self, pasta=AUTOSTART):
        self.arquivo = Path(pasta) / ARQUIVO

    def ativo(self):
        return self.arquivo.is_file()

    def definir(self, ativo):
        if ativo:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            if not self.ativo() or self.arquivo.read_text(encoding="utf-8") != CONTEUDO:
                self.arquivo.write_text(CONTEUDO, encoding="utf-8")
        else:
            self.arquivo.unlink(missing_ok=True)
