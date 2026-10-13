"""Sino da barra de titulo: contador de nao lidas e a lista de notificacoes."""
from datetime import datetime

from gi.repository import Gio, Gtk

from . import tema
from .widgets import botao, css, data_br, icone, rotulo

ICONES = {"atualizacao": "software-update-available-symbolic", "sucesso": "emblem-ok-symbolic",
          "info": "dialog-information-symbolic"}


def ha_quanto(quando, agora=None):
    s = int(((agora or datetime.now()) - quando).total_seconds())
    if s < 60:
        return "agora"
    if s < 3600:
        return f"há {s // 60} min"
    if s < 86400:
        return f"há {s // 3600} h"
    if s < 2 * 86400:
        return "ontem"
    return data_br(quando, hora=False)


class Sino(Gtk.MenuButton):
    def __init__(self, servico, ao_acao):
        super().__init__(relief=Gtk.ReliefStyle.NONE, tooltip_text="Notificações")
        css(self, "ms-sino")
        self.servico, self.ao_acao = servico, ao_acao
        sobre = Gtk.Overlay()
        sino = Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(tema.SINO))),
                                        Gtk.IconSize.BUTTON)
        sino.set_margin_start(6)
        sino.set_margin_end(8)
        sino.set_margin_top(6)
        sino.set_margin_bottom(2)
        sobre.add(sino)
        self.contador = css(Gtk.Label(halign=Gtk.Align.END, valign=Gtk.Align.START), "ms-sino-contador")
        self.contador.set_no_show_all(True)
        sobre.add_overlay(self.contador)
        self.add(sobre)

        self.pop = css(Gtk.Popover(), "ms-notificacoes")
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        caixa.set_size_request(380, -1)
        cab = css(Gtk.Box(spacing=8), "ms-notificacoes-cab")
        cab.pack_start(rotulo("Notificações", ["ms-card-nome"]), True, True, 0)
        self.btn_limpar = botao("Limpar", "ms-fantasma", "ms-pequeno", ao_clicar=self._limpar)
        cab.pack_end(self.btn_limpar, False, False, 0)
        caixa.pack_start(cab, False, False, 0)
        caixa.pack_start(Gtk.Separator(), False, False, 0)
        self.rolagem = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                          propagate_natural_height=True, max_content_height=420)
        self.lista = css(Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE), "ms-notificacoes-lista")
        self.lista.connect("row-activated", self._clicou)
        self.rolagem.add(self.lista)
        caixa.pack_start(self.rolagem, False, False, 0)
        self.vazio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=32)
        self.vazio.pack_start(css(Gtk.Image.new_from_gicon(
            Gio.FileIcon.new(Gio.File.new_for_path(str(tema.SINO))), Gtk.IconSize.DIALOG), "ms-dim"),
            False, False, 0)
        self.vazio.pack_start(rotulo("Nenhuma notificação", ["ms-card-nome"], xalign=0.5), False, False, 0)
        self.vazio.pack_start(rotulo("Avisos de versão nova e novidades aparecem aqui.",
                                     ["ms-dim", "ms-pequeno"], xalign=0.5, wrap=True), False, False, 0)
        caixa.pack_start(self.vazio, False, False, 0)
        caixa.show_all()
        self.pop.add(caixa)
        self.set_popover(self.pop)
        self.pop.connect("closed", lambda _p: (self.servico.marcar_lidas(), self.atualizar()))
        self.connect("toggled", lambda _b: self.get_active() and self._preencher())
        self.atualizar()

    def atualizar(self):
        n = self.servico.nao_lidas()
        self.contador.set_text("9+" if n > 9 else str(n))
        self.contador.set_visible(n > 0)
        self.set_tooltip_text(f"Notificações ({n} não lida{'s' if n != 1 else ''})" if n else "Notificações")
        if self.pop.get_visible():
            self._preencher()

    def _preencher(self):
        for f in self.lista.get_children():
            f.destroy()
        itens = self.servico.listar()
        for n in itens:
            self.lista.add(self._linha(n))
        self.lista.show_all()
        self.rolagem.set_visible(bool(itens))
        self.vazio.set_visible(not itens)
        self.btn_limpar.set_visible(bool(itens))

    def _linha(self, n):
        linha = Gtk.ListBoxRow(activatable=bool(n.acao))
        linha.notificacao = n
        css(linha, "ms-notificacao", *([] if n.lida else ["ms-nao-lida"]))
        caixa = Gtk.Box(spacing=12)
        bolha = css(Gtk.Box(valign=Gtk.Align.START), "ms-notificacao-icone", f"ms-tipo-{n.tipo}")
        bolha.pack_start(icone(ICONES.get(n.tipo, ICONES["info"]), Gtk.IconSize.LARGE_TOOLBAR), True, True, 0)
        caixa.pack_start(bolha, False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        textos.pack_start(rotulo(n.titulo, ["ms-notificacao-titulo"], wrap=True), False, False, 0)
        if n.texto:
            textos.pack_start(rotulo(n.texto, ["ms-dim", "ms-pequeno"], wrap=True), False, False, 0)
        textos.pack_start(rotulo(ha_quanto(n.criada_em), ["ms-dim", "ms-pequeno"]), False, False, 0)
        caixa.pack_start(textos, True, True, 0)
        if not n.lida:
            caixa.pack_end(css(Gtk.Box(valign=Gtk.Align.CENTER), "ms-ponto-nao-lida"), False, False, 0)
        linha.add(caixa)
        return linha

    def _clicou(self, _lista, linha):
        self.pop.popdown()
        self.ao_acao(linha.notificacao)

    def _limpar(self):
        self.servico.limpar()
        self.atualizar()
        self._preencher()
