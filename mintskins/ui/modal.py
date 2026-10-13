"""Modais da janela: um cartao no centro, com o resto do app borrado atras."""
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .widgets import botao, css, icone, rotulo  # noqa: E402

TINTA = {"escura": (20 / 255, 21 / 255, 31 / 255, 0.55), "clara": (247 / 255, 246 / 255, 241 / 255, 0.55)}


def _desfocar(pix):
    """Desfoque barato: reduz muito e amplia de novo, duas vezes."""
    w, h = pix.get_width(), pix.get_height()
    pw, ph = max(1, w // 14), max(1, h // 14)
    p = pix.scale_simple(pw, ph, GdkPixbuf.InterpType.HYPER)
    p = p.scale_simple(max(1, w // 4), max(1, h // 4), GdkPixbuf.InterpType.BILINEAR)
    return p.scale_simple(pw, ph, GdkPixbuf.InterpType.HYPER)


class Vidro(Gtk.DrawingArea):
    """Desenha uma foto borrada do widget de baixo e engole os cliques."""

    def __init__(self, alvo):
        super().__init__()
        self.alvo, self.tinta = alvo, TINTA["escura"]
        self._foto, self._tam, self._agendado = None, None, False
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        for sinal in ("button-press-event", "button-release-event", "scroll-event"):
            self.connect(sinal, lambda *_: True)

    def fotografar(self):
        self._agendado = False
        w, h = self.alvo.get_allocated_width(), self.alvo.get_allocated_height()
        if w < 2 or h < 2:
            return False
        esc = self.alvo.get_scale_factor()
        sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, w * esc, h * esc)
        sup.set_device_scale(esc, esc)
        self.alvo.draw(cairo.Context(sup))
        pix = Gdk.pixbuf_get_from_surface(sup, 0, 0, w * esc, h * esc)
        self._foto, self._tam = (_desfocar(pix) if pix else None), (w, h)
        self.queue_draw()
        return False

    def do_draw(self, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        if self._foto and self._tam == (w, h):
            cr.save()
            cr.scale(w / self._foto.get_width(), h / self._foto.get_height())
            Gdk.cairo_set_source_pixbuf(cr, self._foto, 0, 0)
            cr.get_source().set_filter(cairo.FILTER_GOOD)
            cr.get_source().set_extend(cairo.EXTEND_PAD)
            cr.paint()
            cr.restore()
        elif not self._agendado:      # janela mudou de tamanho: tira outra foto
            self._agendado = True
            GLib.idle_add(self.fotografar)
        cr.set_source_rgba(*self.tinta)
        cr.paint()
        return False


class ModalBorrado(Gtk.Revealer):
    """Base: vidro borrado + cartao centralizado. As subclasses enchem self.cartao."""

    def __init__(self, alvo, ao_fechar=None, largura=520):
        super().__init__(transition_type=Gtk.RevealerTransitionType.CROSSFADE, transition_duration=180)
        self.set_no_show_all(True)
        self._ao_fechar = ao_fechar
        self.ocupado = False
        camada = Gtk.Overlay()
        self.vidro = Vidro(alvo)
        camada.add(self.vidro)
        self.cartao = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                                  halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER), "ms-popup")
        self.cartao.set_size_request(largura, -1)
        camada.add_overlay(self.cartao)
        self.add(camada)
        self.connect("notify::child-revealed", self._revelou)

    @property
    def aberto(self):
        return self.get_visible() and self.get_reveal_child()

    def abrir(self, variante):
        self.vidro.tinta = TINTA.get(variante, TINTA["escura"])
        if not self.aberto:
            self.vidro.fotografar()
            self.set_visible(True)
            self.get_child().show_all()
            self.set_reveal_child(True)

    def fechar(self):
        if self.ocupado or not self.aberto:
            return
        self.set_reveal_child(False)
        if self._ao_fechar:
            self._ao_fechar()

    def _revelou(self, *_):
        if not self.get_child_revealed() and not self.get_reveal_child():
            self.set_visible(False)


class ModalConfirmacao(ModalBorrado):
    """Pergunta sim/nao. confirmar() chama a acao so se a pessoa confirmar."""

    def __init__(self, alvo, ao_fechar=None):
        super().__init__(alvo, ao_fechar, largura=460)
        topo = Gtk.Box(spacing=16)
        self.icone = css(Gtk.Box(valign=Gtk.Align.START), "ms-popup-icone")
        topo.pack_start(self.icone, False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        self.titulo = rotulo("", ["ms-popup-titulo"], wrap=True)
        self.texto = rotulo("", ["ms-dim"], wrap=True)
        textos.pack_start(self.titulo, False, False, 0)
        textos.pack_start(self.texto, False, False, 0)
        topo.pack_start(textos, True, True, 0)
        self.cartao.pack_start(topo, False, False, 0)
        self.botoes = Gtk.Box(spacing=8)
        self.cartao.pack_start(self.botoes, False, False, 0)

    def confirmar(self, variante, titulo, texto, botao_txt, acao, icone_nome="dialog-question-symbolic",
                  destrutivo=False):
        for f in self.icone.get_children() + self.botoes.get_children():
            f.destroy()
        self.icone.pack_start(icone(icone_nome, Gtk.IconSize.DND), True, True, 0)
        self.titulo.set_text(titulo)
        self.texto.set_text(texto)

        def sim():
            self.fechar()
            GLib.idle_add(lambda: acao() and False)

        ok = botao(botao_txt, "ms-perigo" if destrutivo else "ms-primario", ao_clicar=sim)
        self.botoes.pack_end(ok, False, False, 0)
        self.botoes.pack_end(botao("Cancelar", "ms-secundario", ao_clicar=self.fechar), False, False, 0)
        self.abrir(variante)
        self.cartao.show_all()
        ok.grab_focus()
