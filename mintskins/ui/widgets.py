"""Widgets reutilizaveis da janela."""
import math

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def data_br(d, hora=True):
    if not d:
        return "—"
    txt = f"{d.day:02d} {MESES[d.month - 1]} {d.year}"
    return f"{txt}, {d.hour:02d}:{d.minute:02d}" if hora else txt


def css(widget, *classes):
    for c in classes:
        widget.get_style_context().add_class(c)
    return widget


def rotulo(texto="", classes=(), xalign=0.0, wrap=False):
    l = Gtk.Label(label=texto, xalign=xalign)
    if wrap:
        l.set_line_wrap(True)
        l.set_max_width_chars(70)
    else:
        l.set_ellipsize(3)  # Pango.EllipsizeMode.END
    return css(l, *classes)


def icone(nome, tamanho=Gtk.IconSize.MENU, *classes):
    return css(Gtk.Image.new_from_icon_name(nome, tamanho), *classes)


def botao(texto, *classes, icone_nome=None, dica=None, ao_clicar=None):
    b = Gtk.Button()
    if icone_nome:
        caixa = Gtk.Box(spacing=6)
        caixa.pack_start(Gtk.Image.new_from_icon_name(icone_nome, Gtk.IconSize.BUTTON), False, False, 0)
        if texto:
            caixa.pack_start(Gtk.Label(label=texto), False, False, 0)
        b.add(caixa)
    else:
        b.set_label(texto)
    if dica:
        b.set_tooltip_text(dica)
    if ao_clicar:
        b.connect("clicked", lambda _b: ao_clicar())
    return css(b, *classes)


class Marca(Gtk.Image):
    """Logotipo em SVG, desenhado na escala da tela (nitido em HiDPI)."""
    def __init__(self, arquivo, largura):
        super().__init__()
        self.largura = largura
        self.connect("notify::scale-factor", lambda *_: self.definir(self._arquivo))
        self.definir(arquivo)

    def definir(self, arquivo):
        self._arquivo = arquivo
        escala = max(1, self.get_scale_factor())
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(arquivo), self.largura * escala, -1, True)
        except GLib.Error:
            self.clear()
            return
        self.set_from_surface(Gdk.cairo_surface_create_from_pixbuf(pix, escala, None))


class Capa(Gtk.DrawingArea):
    """Imagem com cantos arredondados que preenche o espaco (modo 'cobrir')."""

    def __init__(self, largura, altura, raio=14, so_topo=False):
        super().__init__()
        self.set_size_request(largura, altura)
        self.raio, self.so_topo = raio, so_topo
        self._orig = None
        self._cache = (None, None)
        self.connect("draw", self._desenhar)

    def definir(self, caminho):
        try:
            self._orig = GdkPixbuf.Pixbuf.new_from_file(str(caminho)) if caminho else None
        except GLib.Error:
            self._orig = None
        self._cache = (None, None)
        self.queue_draw()

    def _desenhar(self, _w, cr):
        a = self.get_allocation()
        w, h, r = a.width, a.height, self.raio
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        if self.so_topo:
            cr.line_to(w, h)
            cr.line_to(0, h)
        else:
            cr.arc(w - r, h - r, r, 0, math.pi / 2)
            cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.clip()
        if self._orig is None:
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.18)
            cr.paint()
            return
        escala = self.get_scale_factor()
        if self._cache[0] != (w, h, escala):
            pw, ph = self._orig.get_width(), self._orig.get_height()
            k = max(w * escala / pw, h * escala / ph)
            nw, nh = max(1, round(pw * k)), max(1, round(ph * k))
            pix = self._orig.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
            self._cache = ((w, h, escala), Gdk.cairo_surface_create_from_pixbuf(pix, escala, None))
        sup = self._cache[1]
        sw, sh = sup.get_width() / escala, sup.get_height() / escala
        cr.set_source_surface(sup, (w - sw) / 2, (h - sh) / 2)
        cr.paint()


def menu_popover(relativo, itens):
    """Popover com botoes. itens = [(texto, callback[, destrutivo])] ou None (separador)."""
    pop = Gtk.Popover(relative_to=relativo)
    caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=6), "ms-menu")
    for item in itens:
        if item is None:
            caixa.pack_start(Gtk.Separator(margin_top=4, margin_bottom=4), False, False, 0)
            continue
        texto, cb, destrutivo = (tuple(item) + (False,))[:3]
        b = Gtk.ModelButton(text=texto)
        if destrutivo:
            css(b, "ms-perigo")
        b.connect("clicked", lambda _b, cb=cb: (pop.popdown(), GLib.idle_add(cb)))
        caixa.pack_start(b, False, False, 0)
    caixa.show_all()
    pop.add(caixa)
    return pop


class Card(Gtk.FlowBoxChild):
    """Card de skin, usado em todas as grades (local, galeria, conta, perfil)."""

    def __init__(self, capa, titulo, autor, detalhe="", selos=(), principal=None, favorito=None,
                 menu=None, destaque=False, cadeado=False, ao_abrir=None, ao_autor=None, dica=""):
        super().__init__()
        self.titulo = titulo
        self.set_valign(Gtk.Align.START)
        card = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "ms-card")
        if destaque:
            css(card, "ms-ativa")

        sobre = Gtk.Overlay()
        img = Capa(300, 169, raio=15, so_topo=True)
        img.definir(capa)
        if ao_abrir:
            caixa = Gtk.EventBox()
            caixa.add(img)
            caixa.connect("button-release-event", lambda *_: ao_abrir())
            caixa.connect("realize", lambda w: w.get_window().set_cursor(
                Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
            caixa.set_tooltip_text("Ver detalhes")
            sobre.add(caixa)
        else:
            sobre.add(img)
        linha = Gtk.Box(spacing=6, halign=Gtk.Align.START, valign=Gtk.Align.START, margin=10)
        for texto, forte in selos:
            linha.pack_start(css(Gtk.Label(label=texto), "ms-badge", *(["ms-destaque"] if forte else [])),
                             False, False, 0)
        sobre.add_overlay(linha)
        if cadeado:
            c = css(Gtk.Box(halign=Gtk.Align.END, valign=Gtk.Align.START, margin=10), "ms-badge")
            c.pack_start(icone("changes-prevent-symbolic"), False, False, 0)
            c.set_tooltip_text("Skin oficial: não pode ser editada")
            sobre.add_overlay(c)
        card.pack_start(sobre, False, False, 0)

        corpo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, margin=14, margin_top=12)
        nome = rotulo(titulo, ["ms-card-nome"])
        nome.set_tooltip_text(dica or titulo)
        corpo.pack_start(nome, False, False, 0)
        corpo.pack_start(link(f"por {autor}", ao_autor), False, False, 0)
        if detalhe:
            corpo.pack_start(rotulo(detalhe, ["ms-dim", "ms-pequeno"]), False, False, 0)

        acoes = Gtk.Box(spacing=6, margin_top=10)
        if principal:
            texto, cb, estilo = principal
            b = botao(texto, estilo, ao_clicar=cb)
            b.set_sensitive(cb is not None)
            acoes.pack_start(b, False, False, 0)
        if menu:
            mais = css(Gtk.MenuButton(relief=Gtk.ReliefStyle.NONE), "ms-fantasma")
            mais.add(Gtk.Image.new_from_icon_name("view-more-symbolic", Gtk.IconSize.BUTTON))
            mais.set_tooltip_text("Mais opções")
            mais.set_popover(menu_popover(mais, menu))
            acoes.pack_end(mais, False, False, 0)
        if favorito:
            acoes.pack_end(BotaoFavorito(*favorito), False, False, 0)
        corpo.pack_start(acoes, False, False, 0)
        card.pack_start(corpo, False, False, 0)
        self.add(card)


class BotaoFavorito(Gtk.Button):
    def __init__(self, ativo, ao_mudar, contagem=None):
        super().__init__(relief=Gtk.ReliefStyle.NONE)
        css(self, "ms-fantasma", "ms-favorito")
        caixa = Gtk.Box(spacing=4)
        nome = "starred-symbolic" if ativo else "non-starred-symbolic"
        caixa.pack_start(Gtk.Image.new_from_icon_name(nome, Gtk.IconSize.BUTTON), False, False, 0)
        if contagem is not None:
            caixa.pack_start(Gtk.Label(label=str(contagem)), False, False, 0)
        self.add(caixa)
        if ativo:
            css(self, "ms-favorito-ativo")
        self.set_tooltip_text("Remover das favoritas" if ativo else "Favoritar")
        self.connect("clicked", lambda _b: ao_mudar(not ativo))


def link(texto, ao_clicar=None, classes=("ms-dim", "ms-pequeno")):
    if not ao_clicar:
        return rotulo(texto, list(classes))
    b = css(Gtk.Button(relief=Gtk.ReliefStyle.NONE, halign=Gtk.Align.START), "ms-link")
    b.add(rotulo(texto, list(classes)))
    b.connect("clicked", lambda _b: ao_clicar())
    return b


class Avatar(Gtk.Label):
    def __init__(self, iniciais, grande=False):
        super().__init__(label=iniciais)
        css(self, "ms-avatar", *(["ms-avatar-grande"] if grande else []))
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.CENTER)


def vazio(titulo, texto, acao=None):
    caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "ms-vazio-card")
    caixa.pack_start(rotulo(titulo, ["ms-card-nome"], xalign=0.5), False, False, 0)
    caixa.pack_start(rotulo(texto, ["ms-dim"], xalign=0.5, wrap=True), False, False, 0)
    if acao:
        b = botao(acao[0], "ms-primario", ao_clicar=acao[1])
        b.set_halign(Gtk.Align.CENTER)
        caixa.pack_start(b, False, False, 6)
    return caixa


def grade():
    return Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, column_spacing=20,
                       row_spacing=20, min_children_per_line=1, max_children_per_line=4,
                       valign=Gtk.Align.START)


def preencher(grade_, vazio_, cards):
    for f in grade_.get_children():
        f.destroy()
    for c in cards:
        grade_.add(c)
    grade_.show_all()
    grade_.set_visible(bool(cards))
    vazio_.set_visible(not cards)


def tamanho_br(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.1f} {u}".replace(".", ",")
        n /= 1024
    return f"{n:.1f} TB"
