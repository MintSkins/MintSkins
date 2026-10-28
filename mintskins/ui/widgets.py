"""Widgets reutilizaveis da janela."""
import math
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

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


def rotulo(texto="", classes=(), xalign=0.0, wrap=False, cortar=True):
    """cortar=False: o texto nunca vira "…" (rotulos curtos em caixa alta, abas)."""
    l = Gtk.Label(label=texto, xalign=xalign)
    if wrap:
        l.set_line_wrap(True)
        l.set_max_width_chars(70)
    elif cortar:
        l.set_ellipsize(3)  # Pango.EllipsizeMode.END
    return css(l, *classes)


def caixa_alta(texto):
    """Selo em caixa alta. Com letter-spacing, o GTK mede um espaco comum como quebra de linha
    e o rotulo fica com o dobro da altura; o espaco inseparavel evita isso."""
    return texto.upper().replace(" ", "\u00a0")


def icone(nome, tamanho=Gtk.IconSize.MENU, *classes):
    return css(Gtk.Image.new_from_icon_name(nome, tamanho), *classes)


CAIXA_ALTA = {"ms-primario", "ms-secundario", "ms-contorno", "ms-perigo"}


def botao(texto, *classes, icone_nome=None, dica=None, ao_clicar=None, icone_depois=False):
    """Botao do app. Os principais ficam em caixa alta, como no site. icone_nome: nome do tema ou arquivo (Path)."""
    b = Gtk.Button()
    if texto and CAIXA_ALTA & set(classes):
        texto = texto.upper()
    if icone_nome:
        caixa = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        img = (Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(icone_nome))), Gtk.IconSize.BUTTON)
               if isinstance(icone_nome, Path) else Gtk.Image.new_from_icon_name(icone_nome, Gtk.IconSize.BUTTON))
        partes = [img]
        if texto:
            partes = [Gtk.Label(label=texto), img] if icone_depois else [img, Gtk.Label(label=texto)]
        for p in partes:
            caixa.pack_start(p, False, False, 0)
        b.add(caixa)
    else:
        b.set_label(texto)
    if dica:
        b.set_tooltip_text(dica)
    if ao_clicar:
        b.connect("clicked", lambda _b: ao_clicar())
    return css(b, *classes)


def display(texto, tamanho="m", classes=(), wrap=True):
    """Titulo grande, condensado e em caixa alta (o "display" do site)."""
    # o espaco da fonte condensada e estreito demais; o site abre com word-spacing
    l = rotulo(texto.upper().replace(" ", "\u2005"), ["ms-display", f"ms-display-{tamanho}", *classes], wrap=wrap,
               cortar=False)
    if wrap:
        l.set_max_width_chars(24)
    return l


def sobrelinha(texto):
    """Traco amarelo + rotulo em caixa alta, antes dos titulos de secao."""
    caixa = Gtk.Box(spacing=10)
    caixa.pack_start(css(Gtk.Box(valign=Gtk.Align.CENTER), "ms-traco"), False, False, 0)
    caixa.pack_start(rotulo(texto.upper(), ["ms-sobrelinha"], cortar=False), False, False, 0)
    return caixa


def rotulo_tecnico(destaque, *resto):
    """Ex.: SKIN EM DESTAQUE · 01 / 05 (a primeira parte em amarelo)."""
    caixa = Gtk.Box(spacing=0)
    if destaque:
        caixa.pack_start(rotulo(destaque.upper(), ["ms-sobrelinha"], cortar=False), False, False, 0)
    partes = [p for p in resto if p]
    if partes:
        texto = " · ".join(p.upper() for p in partes)
        caixa.pack_start(rotulo(f" · {texto}" if destaque else texto, ["ms-rotulo-tecnico"], cortar=False),
                         False, False, 0)
    return caixa


def numeros(itens):
    """Quadro de numeros lado a lado: [(rotulo, valor)]."""
    caixa = css(Gtk.Box(homogeneous=True), "ms-numeros")
    for i, (nome, valor) in enumerate(itens):
        c = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4), "ms-numero",
                *(["ms-ultimo"] if i == len(itens) - 1 else []))
        c.pack_start(rotulo(nome.upper(), ["ms-rotulo-tecnico"]), False, False, 0)
        c.pack_start(rotulo(str(valor), ["ms-numero-valor"]), False, False, 0)
        caixa.pack_start(c, True, True, 0)
    return caixa


def opcao(icone_nome, titulo, texto, escolhida=False, ao_clicar=None):
    """Cartao clicavel para escolher entre poucas opcoes (ex.: onde a skin fica)."""
    b = css(Gtk.Button(), "ms-opcao", *(["ms-escolhida"] if escolhida else []))
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    topo = Gtk.Box(spacing=8)
    topo.pack_start(css(Gtk.Image.new_from_icon_name(icone_nome, Gtk.IconSize.LARGE_TOOLBAR), "ms-opcao-icone"),
                    False, False, 0)
    if escolhida:
        topo.pack_end(css(Gtk.Image.new_from_icon_name("object-select-symbolic", Gtk.IconSize.BUTTON),
                          "ms-opcao-icone"), False, False, 0)
    caixa.pack_start(topo, False, False, 0)
    caixa.pack_start(rotulo(titulo.upper(), ["ms-titulo-cartao"], cortar=False), False, False, 0)
    caixa.pack_start(rotulo(texto, ["ms-dim", "ms-pequeno"], wrap=True), False, False, 0)
    b.add(caixa)
    if ao_clicar:
        b.connect("clicked", lambda _b: ao_clicar())
    return b


def ponteiro(widget):
    """Cursor de mao sobre a area clicavel."""
    widget.connect("realize", lambda w: w.get_window().set_cursor(
        Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
    return widget


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

    def __init__(self, largura, altura, raio=8, so_topo=False, escurecer=False):
        super().__init__()
        self.set_size_request(largura, altura)
        self.raio, self.so_topo, self.escurecer = raio, so_topo, escurecer
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
        if self.escurecer:      # texto claro por cima: escurece a esquerda e o rodape (como a vitrine do site)
            for grad in (cairo.LinearGradient(0, 0, w, 0), cairo.LinearGradient(0, h, 0, 0)):
                grad.add_color_stop_rgba(0, 9 / 255, 9 / 255, 12 / 255, 0.92)
                grad.add_color_stop_rgba(0.45, 9 / 255, 9 / 255, 12 / 255, 0.45)
                grad.add_color_stop_rgba(1, 9 / 255, 9 / 255, 12 / 255, 0.0)
                cr.set_source(grad)
                cr.paint()


def menu_popover(relativo, itens):
    """Popover com botoes. itens = [(texto, callback[, destrutivo])] ou None (separador)."""
    pop = css(Gtk.Popover(relative_to=relativo), "ms-pop")
    caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "ms-menu")
    for item in itens:
        if item is None:
            caixa.pack_start(Gtk.Separator(), False, False, 0)
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


class Card(Gtk.EventBox):
    """Card de skin, usado em todas as grades e trilhos (local, galeria, conta, perfil).

    Como no site: a capa e o nome abrem a skin; embaixo, autor, numeros e a acao principal.
    """
    LARGURA = 296

    def __init__(self, capa, titulo, autor, detalhe="", selos=(), principal=None, favorito=None,
                 menu=None, destaque=False, cadeado=False, ao_abrir=None, ao_autor=None, dica="",
                 numeros_=(), etiquetas=(), na_conta=None):
        super().__init__(visible_window=False)
        self.titulo = titulo
        self.set_valign(Gtk.Align.START)
        card = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0), "ms-card")
        card.set_size_request(self.LARGURA, -1)
        if destaque:
            css(card, "ms-ativa")

        sobre = css(Gtk.Overlay(), "ms-card-capa")
        img = Capa(self.LARGURA, round(self.LARGURA * 9 / 16), raio=8)
        img.definir(capa)
        sobre.add(img)
        linha = Gtk.Box(spacing=6, halign=Gtk.Align.START, valign=Gtk.Align.START, margin=10)
        for texto, forte in selos:
            linha.pack_start(css(Gtk.Label(label=caixa_alta(texto)), "ms-badge", *(["ms-destaque"] if forte else [])),
                             False, False, 0)
        sobre.add_overlay(linha)
        if cadeado:
            c = css(Gtk.Box(halign=Gtk.Align.END, valign=Gtk.Align.START, margin=10), "ms-badge")
            c.pack_start(icone("changes-prevent-symbolic"), False, False, 0)
            c.set_tooltip_text("Skin oficial: não pode ser editada")
            sobre.add_overlay(c)
        if ao_abrir:
            # a capa inteira e um botao: clicar nela abre a skin, igual ao nome
            clique = ponteiro(css(Gtk.Button(relief=Gtk.ReliefStyle.NONE), "ms-capa-botao"))
            clique.add(sobre)
            clique.connect("clicked", lambda _b: ao_abrir())
            clique.set_tooltip_text(dica or "Ver a skin")
            card.pack_start(clique, False, False, 0)
        else:
            card.pack_start(sobre, False, False, 0)

        corpo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=12)
        topo = Gtk.Box(spacing=8)
        nome = link(titulo, ao_abrir, ("ms-card-nome",)) if ao_abrir else rotulo(titulo, ["ms-card-nome"])
        nome.set_tooltip_text(dica or titulo)
        topo.pack_start(nome, True, True, 0)
        for texto, publica in etiquetas:
            topo.pack_end(css(Gtk.Label(label=caixa_alta(texto), valign=Gtk.Align.CENTER), "ms-etiqueta",
                              *(["ms-publica"] if publica else [])), False, False, 0)
        corpo.pack_start(topo, False, False, 0)

        meta = Gtk.Box(spacing=12)
        meta.pack_start(link(f"por {autor}", ao_autor), False, False, 0)
        if detalhe:
            meta.pack_start(rotulo(detalhe, ["ms-apagado", "ms-pequeno"]), False, False, 0)
        for icone_nome, valor in numeros_:
            n = css(Gtk.Box(spacing=4), "ms-card-numeros")
            n.pack_start(icone(icone_nome), False, False, 0)
            n.pack_start(Gtk.Label(label=str(valor)), False, False, 0)
            meta.pack_start(n, False, False, 0)
        corpo.pack_start(meta, False, False, 0)

        acoes = Gtk.Box(spacing=6, margin_top=8)
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
        if na_conta:        # publicar, deixar privada, guardar ou remover da conta (abre o modal)
            from . import tema
            b = css(Gtk.Button(relief=Gtk.ReliefStyle.NONE), "ms-fantasma")
            b.add(Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(tema.TROCA))),
                                           Gtk.IconSize.BUTTON))
            b.set_tooltip_text("Na conta: publicar, deixar privada, guardar ou remover")
            b.connect("clicked", lambda _b: na_conta())
            acoes.pack_end(b, False, False, 0)
        if favorito:
            acoes.pack_end(BotaoFavorito(*favorito), False, False, 0)
        corpo.pack_start(acoes, False, False, 0)
        card.pack_start(corpo, False, False, 0)
        self.add(card)


def trilho(cards, vazio_=None):
    """Fileira horizontal de cards (como os trilhos do site), com setas para andar."""
    rol = Gtk.ScrolledWindow(vscrollbar_policy=Gtk.PolicyType.NEVER,
                             hscrollbar_policy=Gtk.PolicyType.EXTERNAL)
    fila = Gtk.Box(spacing=20)
    for c in cards:
        fila.pack_start(c, False, False, 0)
    rol.add(fila)
    rol.set_size_request(-1, 300)

    def andar(direcao):
        adj = rol.get_hadjustment()
        passo = max(Card.LARGURA + 20, adj.get_page_size() - Card.LARGURA / 2)
        alvo = min(max(adj.get_lower(), adj.get_value() + direcao * passo), adj.get_upper() - adj.get_page_size())
        inicio, quadros = adj.get_value(), [0]

        def passo_animado():
            quadros[0] += 1
            t = min(1, quadros[0] / 14)
            adj.set_value(inicio + (alvo - inicio) * (1 - (1 - t) ** 3))
            return t < 1
        GLib.timeout_add(16, passo_animado)

    setas = Gtk.Box(spacing=6)
    anterior = botao("", "ms-contorno", "ms-icone-quadrado", icone_nome="go-previous-symbolic",
                     dica="Anteriores", ao_clicar=lambda: andar(-1))
    proxima = botao("", "ms-contorno", "ms-icone-quadrado", icone_nome="go-next-symbolic",
                    dica="Próximas", ao_clicar=lambda: andar(1))

    def conferir(adj):
        anterior.set_sensitive(adj.get_value() > adj.get_lower() + 1)
        proxima.set_sensitive(adj.get_value() < adj.get_upper() - adj.get_page_size() - 1)
        setas.set_visible(adj.get_upper() - adj.get_lower() > adj.get_page_size() + 1)
    for sinal in ("value-changed", "changed"):
        rol.get_hadjustment().connect(sinal, conferir)
    setas.pack_start(anterior, False, False, 0)
    setas.pack_start(proxima, False, False, 0)
    setas.set_no_show_all(True)
    for b in (anterior, proxima):
        b.show_all()
    return rol, setas


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
    def __init__(self, iniciais, grande=False, pequeno=False):
        super().__init__(label=iniciais)
        css(self, "ms-avatar", *(["ms-avatar-grande"] if grande else []), *(["ms-avatar-pequeno"] if pequeno else []))
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.CENTER)


def avatar(quem, grande=False, pequeno=False):
    """Foto redonda da conta/perfil; sem foto, as iniciais."""
    if getattr(quem, "foto", None):
        lado = 72 if grande else 28 if pequeno else 36
        c = Capa(lado, lado, raio=lado / 2)
        c.definir(quem.foto)
        c.set_halign(Gtk.Align.START)
        c.set_valign(Gtk.Align.CENTER)
        return c
    return Avatar(quem.iniciais, grande, pequeno)


def vazio(titulo, texto, acao=None):
    caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "ms-vazio-card")
    caixa.pack_start(rotulo(titulo.upper(), ["ms-display", "ms-display-xs"], xalign=0.5), False, False, 0)
    caixa.pack_start(rotulo(texto, ["ms-dim"], xalign=0.5, wrap=True), False, False, 0)
    if acao:
        b = botao(acao[0], "ms-primario", ao_clicar=acao[1])
        b.set_halign(Gtk.Align.CENTER)
        caixa.pack_start(b, False, False, 6)
    return caixa


def grade():
    return Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True, column_spacing=20,
                       row_spacing=28, min_children_per_line=1, max_children_per_line=5,
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
