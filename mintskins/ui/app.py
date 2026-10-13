"""Gtk.Application: inicia a janela com o servico ja montado (injecao de dependencia)."""
import sys
import traceback

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gio, GLib, Gtk  # noqa: E402

from ..dominio.erros import MintSkinsErro  # noqa: E402
from . import bandeja  # noqa: E402
from .janela import Janela  # noqa: E402

APP_ID = "io.github.pabluoo.MintSkins"


class App(Gtk.Application):
    def __init__(self, app, oculto=False):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.app = app
        self.janela = None
        self.bandeja = None
        self._oculto = oculto     # aberto pelo sistema ao ligar: so o icone, sem janela

    def do_startup(self):
        Gtk.Application.do_startup(self)
        try:
            self.app.skins.migrar_legado()
        except Exception:  # noqa: BLE001 — a migração nunca impede o app de abrir
            traceback.print_exc()
        if bandeja.disponivel():
            self.bandeja = bandeja.Bandeja(ao_abrir=self.do_activate, ao_sair=self.sair)
            self.bandeja.mostrar(self.app.skins.preferencias().segundo_plano)
        prefs = self.app.skins.preferencias()
        try:
            self.app.inicio_automatico.definir(prefs.iniciar_com_sistema)
        except OSError:
            traceback.print_exc()
        acao = Gio.SimpleAction.new("atualizacao", None)
        acao.connect("activate", lambda *_: self._abrir_atualizacao())
        self.add_action(acao)

    def em_segundo_plano(self):
        """Fechar a janela so esconde, se houver icone na bandeja e a preferencia deixar."""
        return self.bandeja is not None and self.app.skins.preferencias().segundo_plano

    def mostrar_bandeja(self, visivel):
        if self.bandeja:
            self.bandeja.mostrar(visivel)

    def _abrir_atualizacao(self):
        self.do_activate()
        GLib.idle_add(self.janela.mostrar_atualizacao)

    def sair(self):
        if self.janela and self.janela.ocupado:
            self.do_activate()
            self.janela.avisar("Espere a tarefa em andamento terminar para sair.")
            return
        self.quit()

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
            if self._oculto and self.em_segundo_plano():
                self._oculto = False
                return
        self._oculto = False
        self.janela.present()

    def do_open(self, arquivos, _n, _dica):
        self.do_activate()
        if self.janela:
            for f in arquivos:
                if f.get_path():
                    self.janela.importar_arquivo(f.get_path())


def main(app, argv=None, oculto=False):
    return App(app, oculto).run(argv if argv is not None else sys.argv)
