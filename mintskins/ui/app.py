"""Gtk.Application: inicia a janela com o servico ja montado (injecao de dependencia)."""
import sys
import traceback

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gio, Gtk  # noqa: E402

from ..dominio.erros import MintSkinsErro  # noqa: E402
from .janela import Janela  # noqa: E402

APP_ID = "io.github.pabluoo.MintSkins"


class App(Gtk.Application):
    def __init__(self, app):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.app = app
        self.janela = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        try:
            self.app.skins.migrar_legado()
        except Exception:  # noqa: BLE001 — a migração nunca impede o app de abrir
            traceback.print_exc()

    def do_activate(self):
        try:
            self.app.skins.desktop.verificar()
        except MintSkinsErro as e:
            d = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                  text="O MintSkins precisa do Cinnamon")
            d.format_secondary_text(str(e))
            d.run()
            d.destroy()
            return
        if not self.janela:
            self.janela = Janela(self, self.app)
        self.janela.present()

    def do_open(self, arquivos, _n, _dica):
        self.do_activate()
        if self.janela:
            for f in arquivos:
                if f.get_path():
                    self.janela.importar_arquivo(f.get_path())


def main(app, argv=None):
    return App(app).run(argv if argv is not None else sys.argv)
