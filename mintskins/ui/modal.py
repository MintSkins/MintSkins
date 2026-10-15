"""Modais da janela: um cartao no centro, com o resto do app borrado atras."""
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .widgets import botao, css, icone, opcao, rotulo  # noqa: E402

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
                  destrutivo=False, so_ok=False):
        """so_ok: so um botao (aviso ou erro), sem Cancelar."""
        for f in self.icone.get_children() + self.botoes.get_children():
            f.destroy()
        estilo = self.icone.get_style_context()
        (estilo.add_class if destrutivo else estilo.remove_class)("ms-perigo")
        self.icone.pack_start(icone(icone_nome, Gtk.IconSize.DND), True, True, 0)
        self.titulo.set_text(titulo)
        self.texto.set_text(texto)

        def sim():
            self.fechar()
            if acao:
                GLib.idle_add(lambda: acao() and False)

        ok = botao(botao_txt, "ms-perigo" if destrutivo else "ms-primario", ao_clicar=sim)
        self.botoes.pack_end(ok, False, False, 0)
        if not so_ok:
            self.botoes.pack_end(botao("Cancelar", "ms-contorno", ao_clicar=self.fechar), False, False, 0)
        self.abrir(variante)
        self.cartao.show_all()
        ok.grab_focus()


DESCRICAO_MAXIMA = 2000   # o mesmo limite do site


class CaixaDeTexto:
    """Campo de varias linhas, com quebra de linha e contador (para descricoes)."""

    def __init__(self, pai, titulo, exemplo, maximo):
        self.maximo = maximo
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        cab = Gtk.Box()
        cab.pack_start(rotulo(titulo.upper(), ["ms-rotulo-campo"], cortar=False), False, False, 0)
        self.contador = rotulo("", ["ms-apagado", "ms-pequeno"], cortar=False)
        cab.pack_end(self.contador, False, False, 0)
        caixa.pack_start(cab, False, False, 0)
        rol = css(Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER), "ms-texto-caixa")
        rol.set_size_request(-1, 120)
        self.view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, accepts_tab=False, top_margin=10,
                                 bottom_margin=10, left_margin=12, right_margin=12)
        css(self.view, "ms-texto")
        self.exemplo = rotulo(exemplo, ["ms-apagado"], wrap=True)
        sobre = Gtk.Overlay()
        sobre.add(self.view)
        self.exemplo.set_valign(Gtk.Align.START)
        self.exemplo.set_margin_top(10)
        self.exemplo.set_margin_start(14)
        sobre.add_overlay(self.exemplo)
        sobre.set_overlay_pass_through(self.exemplo, True)
        rol.add(sobre)
        caixa.pack_start(rol, False, False, 0)
        pai.pack_start(caixa, False, False, 0)
        self.view.get_buffer().connect("changed", self._mudou)

    def _mudou(self, buf):
        texto = self.texto()
        if len(texto) > self.maximo:                     # corta o que passar do limite (colar um texto grande)
            buf.set_text(texto[:self.maximo])
            return
        self.contador.set_text(f"{len(texto)}/{self.maximo}")
        self.exemplo.set_visible(not texto)

    def texto(self):
        buf = self.view.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

    def definir(self, texto):
        self.view.get_buffer().set_text(texto or "")
        self._mudou(self.view.get_buffer())


class ModalFormulario(ModalBorrado):
    """Nome + descricao (e, ao salvar o visual, se usa uma foto da tela como capa)."""

    def __init__(self, alvo, ao_fechar=None):
        super().__init__(alvo, ao_fechar, largura=500)
        self.titulo = rotulo("", ["ms-popup-titulo"], wrap=True)
        self.cartao.pack_start(self.titulo, False, False, 0)
        self.explicacao = rotulo("", ["ms-dim"], wrap=True)
        self.explicacao.set_no_show_all(True)
        self.cartao.pack_start(self.explicacao, False, False, 0)
        self.nome = self._campo("Nome", "Ex.: Mint escuro com dock", 60)
        self.descricao = CaixaDeTexto(self.cartao, "Descrição", "Opcional — o que tem nela: tema, ícones, dock…",
                                      DESCRICAO_MAXIMA)
        self.foto = Gtk.CheckButton(label="Usar uma foto da tela como capa")
        self.foto.set_no_show_all(True)
        self.cartao.pack_start(self.foto, False, False, 0)
        self.botoes = Gtk.Box(spacing=8)
        self.ok = botao("", "ms-primario", ao_clicar=self._confirmar)
        self.botoes.pack_end(self.ok, False, False, 0)
        self.botoes.pack_end(botao("Cancelar", "ms-contorno", ao_clicar=self.fechar), False, False, 0)
        self.cartao.pack_start(self.botoes, False, False, 0)
        self.nome.connect("changed", lambda e: self.ok.set_sensitive(bool(e.get_text().strip())))
        self.nome.connect("activate", lambda _e: self.ok.get_sensitive() and self._confirmar())

    def _campo(self, titulo, exemplo, maximo):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        caixa.pack_start(rotulo(titulo.upper(), ["ms-rotulo-campo"], cortar=False), False, False, 0)
        e = css(Gtk.Entry(placeholder_text=exemplo, max_length=maximo), "ms-campo")
        caixa.pack_start(e, False, False, 0)
        self.cartao.pack_start(caixa, False, False, 0)
        return e

    def pedir(self, variante, titulo, botao_txt, ao_confirmar, nome="", descricao="", com_capa=False,
              explicacao=None):
        """ao_confirmar(nome, descricao, usar_foto_da_tela)."""
        self._ao_confirmar = ao_confirmar
        self.titulo.set_text(titulo)
        self.explicacao.set_text(explicacao or "")
        self.explicacao.set_visible(bool(explicacao))
        self.nome.set_text(nome)
        self.descricao.definir(descricao)
        self.foto.set_active(True)
        self.foto.set_visible(com_capa)
        self.ok.set_label(botao_txt.upper())
        self.ok.set_sensitive(bool(nome.strip()))
        self.abrir(variante)
        self.descricao.definir(descricao)    # depois de abrir: o show_all mostraria o texto de exemplo
        self.nome.grab_focus()

    def _confirmar(self):
        dados = (self.nome.get_text().strip(), self.descricao.texto().strip(),
                 self.foto.get_visible() and self.foto.get_active())
        self.fechar()
        GLib.idle_add(lambda: self._ao_confirmar(*dados) and False)


class ModalEscolha(ModalBorrado):
    """Escolher uma opcao entre cartoes (ex.: enviar como privada ou publica)."""

    def __init__(self, alvo, ao_fechar=None):
        super().__init__(alvo, ao_fechar, largura=560)
        self.titulo = rotulo("", ["ms-popup-titulo"], wrap=True)
        self.texto = rotulo("", ["ms-dim"], wrap=True)
        self.opcoes = Gtk.Box(spacing=12, homogeneous=True)
        for w in (self.titulo, self.texto, self.opcoes):
            self.cartao.pack_start(w, False, False, 0)
        botoes = Gtk.Box()
        botoes.pack_end(botao("Cancelar", "ms-contorno", ao_clicar=self.fechar), False, False, 0)
        self.cartao.pack_start(botoes, False, False, 0)

    def escolher(self, variante, titulo, texto, opcoes, ao_escolher):
        """opcoes = [(id, icone, titulo, descricao)]; ao_escolher(id)."""
        self.titulo.set_text(titulo)
        self.texto.set_text(texto)
        for f in self.opcoes.get_children():
            f.destroy()

        def escolheu(chave):
            self.fechar()
            GLib.idle_add(lambda: ao_escolher(chave) and False)

        for chave, icone_nome, tit, desc in opcoes:
            self.opcoes.pack_start(opcao(icone_nome, tit, desc, ao_clicar=lambda c=chave: escolheu(c)),
                                   True, True, 0)
        self.abrir(variante)
        self.cartao.show_all()


class ModalAtualizar(ModalBorrado):
    """Atualizar uma skin com o visual da tela: vira a versao seguinte (v2, v3...).

    A capa pode ser uma foto nova da tela, uma imagem do computador ou continuar a mesma.
    """
    CAPAS = [("manter", "object-select-symbolic", "Manter a atual", "A capa continua a mesma."),
             ("tela", "camera-photo-symbolic", "Foto da tela", "Tira uma foto do desktop agora."),
             ("imagem", "image-x-generic-symbolic", "Escolher imagem", "Usa uma imagem do seu computador.")]

    def __init__(self, alvo, ao_fechar=None):
        super().__init__(alvo, ao_fechar, largura=620)
        self.titulo = rotulo("", ["ms-popup-titulo"], wrap=True)
        self.texto = rotulo("", ["ms-dim"], wrap=True)
        self.cartao.pack_start(self.titulo, False, False, 0)
        self.cartao.pack_start(self.texto, False, False, 0)
        self.cartao.pack_start(rotulo("CAPA", ["ms-rotulo-campo"], cortar=False), False, False, 0)
        self.opcoes = Gtk.Box(spacing=10, homogeneous=True)
        self.cartao.pack_start(self.opcoes, False, False, 0)
        self.enviar = Gtk.CheckButton()
        self.enviar.set_no_show_all(True)
        self.cartao.pack_start(self.enviar, False, False, 0)
        botoes = Gtk.Box(spacing=8)
        self.ok = botao("", "ms-primario", ao_clicar=self._confirmar)
        botoes.pack_end(self.ok, False, False, 0)
        botoes.pack_end(botao("Cancelar", "ms-contorno", ao_clicar=self.fechar), False, False, 0)
        self.cartao.pack_start(botoes, False, False, 0)

    def pedir(self, variante, skin, na_conta, ao_confirmar):
        """ao_confirmar(capa: "tela" | "imagem" | "manter", enviar_para_conta: bool)."""
        self._ao_confirmar, self.capa = ao_confirmar, "manter"
        nova = skin.versao + 1
        self.titulo.set_text(f"Atualizar “{skin.nome}”")
        self.texto.set_text(f"Grava o visual que está na tela agora (tema, ícones, painel, dock, papel de parede) "
                            f"por cima da v{skin.versao}. Ela vira a v{nova}.")
        self.enviar.set_label(f"Enviar a v{nova} para a conta (o site também fica atualizado)")
        self.enviar.set_active(na_conta)
        self.enviar.set_visible(na_conta)
        self.ok.set_label(f"SALVAR V{nova}")
        self._desenhar_opcoes()
        self.abrir(variante)
        self.cartao.show_all()

    def _desenhar_opcoes(self):
        for f in self.opcoes.get_children():
            f.destroy()
        for chave, icone_nome, tit, desc in self.CAPAS:
            self.opcoes.pack_start(opcao(icone_nome, tit, desc, escolhida=chave == self.capa,
                                         ao_clicar=lambda c=chave: self._escolher(c)), True, True, 0)
        self.opcoes.show_all()

    def _escolher(self, chave):
        self.capa = chave
        self._desenhar_opcoes()

    def _confirmar(self):
        capa, enviar = self.capa, self.enviar.get_visible() and self.enviar.get_active()
        self.fechar()
        GLib.idle_add(lambda: self._ao_confirmar(capa, enviar) and False)
