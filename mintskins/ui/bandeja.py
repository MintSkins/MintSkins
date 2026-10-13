"""Icone na bandeja do sistema (perto do relogio), para o app rodar em segundo plano.
Clique: abre a janela. Botao direito: menu com Sair."""
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from . import tema  # noqa: E402
from .textos import APP  # noqa: E402

try:                                   # Linux Mint: XApp, nativo do Cinnamon
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp  # noqa: E402
except (ValueError, ImportError):
    XApp = None
try:                                   # outros desktops
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as Indicador  # noqa: E402
except (ValueError, ImportError):
    Indicador = None


def disponivel():
    return XApp is not None or Indicador is not None


def _icone():
    """O icone instalado; rodando do repositorio, o arquivo do simbolo."""
    return "mintskins" if Gtk.IconTheme.get_default().has_icon("mintskins") else str(tema.SIMBOLO)


class Bandeja:
    def __init__(self, ao_abrir, ao_sair):
        self.menu = Gtk.Menu()
        for texto, acao in (("Mostrar aplicativo", ao_abrir), (f"Versão {__version__}", None),
                            ("Fechar", ao_sair)):
            item = Gtk.MenuItem(label=texto)
            if acao:
                item.connect("activate", lambda _i, a=acao: a())
            else:
                item.set_sensitive(False)          # so informa a versao
            self.menu.append(item)
        self.menu.show_all()

        self._xapp = self._ind = None
        if XApp is not None:
            self._xapp = XApp.StatusIcon()
            self._xapp.set_name("mintskins")
            self._xapp.set_icon_name(_icone())
            self._xapp.set_tooltip_text(f"{APP} — clique para abrir")
            self._xapp.set_secondary_menu(self.menu)
            self._xapp.connect("activate", lambda _i, botao, _t: botao == 1 and ao_abrir())
        elif Indicador is not None:
            self._ind = Indicador.Indicator.new("mintskins", _icone(),
                                                Indicador.IndicatorCategory.APPLICATION_STATUS)
            self._ind.set_title(APP)
            self._ind.set_menu(self.menu)

    def mostrar(self, visivel):
        if self._xapp:
            self._xapp.set_visible(visivel)
        elif self._ind:
            self._ind.set_status(Indicador.IndicatorStatus.ACTIVE if visivel
                                 else Indicador.IndicatorStatus.PASSIVE)
