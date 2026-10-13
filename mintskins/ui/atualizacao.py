"""Popup de atualizacao: cartao no centro da janela, com o resto borrado atras."""
import re
from html import escape

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from . import tema  # noqa: E402
from .widgets import Marca, botao, css, rotulo  # noqa: E402

TINTA = {"escura": (20 / 255, 21 / 255, 31 / 255, 0.55), "clara": (247 / 255, 246 / 255, 241 / 255, 0.55)}


def notas_em_markup(md):
    """O texto da release (Markdown do GitHub) em markup Pango simples."""
    linhas, em_codigo = [], False
    for linha in (md or "").replace("\r", "").splitlines():
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
            continue
        if em_codigo or linha.lstrip().startswith("**Full Changelog**"):
            continue
        txt = escape(linha.strip())
        txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
        txt = re.sub(r"`([^`]+)`", r"<tt>\1</tt>", txt)
        txt = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", txt)
        if re.match(r"#{1,6} ", txt):
            txt = "<b>" + txt.lstrip("#").strip() + "</b>"
        elif re.match(r"[-*] ", txt):
            txt = "•  " + txt[2:]
        linhas.append(txt)
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()
    return texto or "Correções e melhorias."


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


class PopupAtualizacao(Gtk.Revealer):
    """Estados: verificando, nova, sem_novidade, progresso, pronto, erro."""

    def __init__(self, alvo, ao_atualizar, ao_pular, ao_reiniciar, ao_tentar_de_novo, ao_fechar=None):
        super().__init__(transition_type=Gtk.RevealerTransitionType.CROSSFADE, transition_duration=180)
        self.set_no_show_all(True)
        self._ao_fechar = ao_fechar
        self.ocupado = False
        camada = Gtk.Overlay()
        self.vidro = Vidro(alvo)
        camada.add(self.vidro)
        self.cartao = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                                  halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER), "ms-popup")
        self.cartao.set_size_request(520, -1)
        camada.add_overlay(self.cartao)
        self.add(camada)

        topo = Gtk.Box(spacing=16)
        topo.pack_start(Marca(tema.SIMBOLO, 56), False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        self.titulo = rotulo("", ["ms-popup-titulo"], wrap=True)
        self.subtitulo = rotulo("", ["ms-dim"], wrap=True)
        textos.pack_start(self.titulo, False, False, 0)
        textos.pack_start(self.subtitulo, False, False, 0)
        topo.pack_start(textos, True, True, 0)
        self.cartao.pack_start(topo, False, False, 0)

        self.pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=120,
                               vhomogeneous=False, interpolate_size=True)
        self.cartao.pack_start(self.pilha, False, False, 0)

        # nova versao: as novidades
        novidades = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        novidades.pack_start(rotulo("NOVIDADES", ["ms-sobrelinha"]), False, False, 0)
        self.notas = rotulo("", ["ms-popup-notas"], wrap=True)
        self.notas.set_max_width_chars(60)
        self.notas.set_valign(Gtk.Align.START)
        self.notas.set_selectable(False)
        rol = css(Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, min_content_height=150,
                                     max_content_height=240, propagate_natural_height=True), "ms-popup-rolagem")
        rol.add(self.notas)
        novidades.pack_start(rol, False, False, 0)
        self.pilha.add_named(novidades, "nova")

        # baixando / instalando / verificando
        prog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        linha = Gtk.Box(spacing=10)
        self.spinner = Gtk.Spinner()
        linha.pack_start(self.spinner, False, False, 0)
        self.passo = rotulo("", ["ms-card-nome"], wrap=True)
        linha.pack_start(self.passo, True, True, 0)
        prog.pack_start(linha, False, False, 0)
        self.barra = Gtk.ProgressBar()
        prog.pack_start(self.barra, False, False, 0)
        self.detalhe = rotulo("", ["ms-dim", "ms-pequeno"], wrap=True)
        prog.pack_start(self.detalhe, False, False, 0)
        self.pilha.add_named(prog, "progresso")

        # mensagem simples (pronto, erro, sem novidade)
        self.mensagem = rotulo("", ["ms-dim"], wrap=True)
        self.pilha.add_named(self.mensagem, "mensagem")

        self.botoes = Gtk.Box(spacing=8)
        self.cartao.pack_start(self.botoes, False, False, 0)
        self._acoes = {
            "atualizar": ("Atualizar agora", "ms-primario", ao_atualizar),
            "depois": ("Depois", "ms-secundario", self.fechar),
            "fechar": ("Fechar", "ms-secundario", self.fechar),
            "pular": ("Pular esta versão", "ms-fantasma", ao_pular),
            "reiniciar": ("Reiniciar agora", "ms-primario", ao_reiniciar),
            "tentar": ("Tentar de novo", "ms-primario", ao_tentar_de_novo),
        }
        self.connect("notify::child-revealed", self._revelou)

    # ---------------------------------------------------------------- abrir / fechar
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

    def _botoes(self, *nomes):
        for f in self.botoes.get_children():
            f.destroy()
        for nome in nomes:
            texto, classe, acao = self._acoes[nome]
            b = botao(texto, classe, ao_clicar=acao)
            if nome == "pular":
                self.botoes.pack_start(b, False, False, 0)
            else:
                self.botoes.pack_end(b, False, False, 0)
        # pack_end inverte a ordem: o botao principal fica na ponta direita
        self.botoes.show_all()

    def _cabecalho(self, titulo, subtitulo):
        self.titulo.set_text(titulo)
        self.subtitulo.set_text(subtitulo)
        self.subtitulo.set_visible(bool(subtitulo))

    # ---------------------------------------------------------------- estados
    def verificando(self):
        self.ocupado = False
        self._cabecalho("Procurando atualizações", f"Você usa o MintSkins {__version__}.")
        self._progresso("Consultando o GitHub…", None, "")
        self._botoes("fechar")

    def nova(self, nova):
        self.ocupado = False
        self.spinner.stop()
        self._cabecalho("Nova versão disponível",
                        f"MintSkins {nova.versao} · você usa a {__version__}")
        self.notas.set_markup(notas_em_markup(nova.notas))
        self.pilha.set_visible_child_name("nova")
        self._botoes("pular", "atualizar", "depois")

    def sem_novidade(self):
        self.ocupado = False
        self.spinner.stop()
        self._cabecalho("Tudo em dia", f"MintSkins {__version__}")
        self.mensagem.set_text("Você já está usando a versão mais recente.")
        self.pilha.set_visible_child_name("mensagem")
        self._botoes("fechar")

    def baixando(self, versao, baixados=0, total=0):
        self.ocupado = True
        self._cabecalho(f"Atualizando para o MintSkins {versao}", "Não feche o MintSkins.")
        mb = 1024 * 1024
        detalhe = f"{baixados / mb:.1f} de {total / mb:.1f} MB" if total else f"{baixados / mb:.1f} MB"
        self._progresso("Baixando a versão nova…", baixados / total if total else None, detalhe)
        self._botoes()

    def instalando(self, versao):
        self.ocupado = True
        self._cabecalho(f"Atualizando para o MintSkins {versao}", "Não feche o MintSkins.")
        self._progresso("Instalando…", None, "Digite sua senha de administrador na janela que abriu.")
        self._botoes()

    def pronto(self, versao):
        self.ocupado = False
        self.spinner.stop()
        self._cabecalho(f"MintSkins {versao} instalado", "")
        self.mensagem.set_text("Reinicie o MintSkins para começar a usar a versão nova.")
        self.pilha.set_visible_child_name("mensagem")
        self._botoes("reiniciar", "depois")

    def erro(self, texto):
        self.ocupado = False
        self.spinner.stop()
        self._cabecalho("Não foi possível atualizar", "")
        self.mensagem.set_text(texto)
        self.pilha.set_visible_child_name("mensagem")
        self._botoes("tentar", "fechar")

    def _progresso(self, passo, fracao, detalhe):
        self.passo.set_text(passo)
        self.detalhe.set_text(detalhe)
        self.detalhe.set_visible(bool(detalhe))
        self.barra.set_visible(fracao is not None)    # sem total conhecido, so o spinner gira
        if fracao is not None:
            self.barra.set_fraction(max(0.0, min(1.0, fracao)))
        self.spinner.start()
        self.pilha.set_visible_child_name("progresso")
