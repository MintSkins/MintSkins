"""Vitrine da tela inicial, como a do mintskins.com: a skin em destaque ocupa o topo e troca sozinha.

A troca so para enquanto o mouse esta em cima de "Ver a skin"; a lista ao lado mostra o tempo de cada uma.
"""
from gi.repository import GLib, Gtk

from .widgets import Capa, botao, css, display, rotulo, rotulo_tecnico

TEMPO = 4500        # ms em cada skin
QUADRO = 40         # ms entre um passo e outro da barrinha de tempo
MAXIMO = 5


class Vitrine(Gtk.Overlay):
    def __init__(self, janela):
        super().__init__()
        self.j = janela
        css(self, "ms-vitrine")
        self.set_size_request(-1, 420)
        self.itens, self.atual, self.decorrido, self.pausada = [], 0, 0, False
        self.fundos = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=500)
        self.add(self.fundos)
        self.textos = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=350,
                                halign=Gtk.Align.START, valign=Gtk.Align.END, margin=40, vhomogeneous=False)
        self.add_overlay(self.textos)
        self.lista = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, halign=Gtk.Align.END,
                                 valign=Gtk.Align.CENTER, margin_end=24), "ms-vitrine-lista")
        self.lista.set_size_request(280, -1)
        self.add_overlay(self.lista)
        self.set_overlay_pass_through(self.lista, False)
        self._relogio = GLib.timeout_add(QUADRO, self._passo)
        self.connect("destroy", lambda *_: GLib.source_remove(self._relogio))

    def definir(self, itens):
        itens = itens[:MAXIMO]
        if [i.id for i in itens] == [i.id for i in self.itens]:
            self.itens = itens          # mesmos destaques: so atualiza os dados, sem voltar ao primeiro
            return
        self.itens, self.atual, self.decorrido = itens, 0, 0
        for pilha in (self.fundos, self.textos, self.lista):
            for f in pilha.get_children():
                f.destroy()
        self.barras, self.botoes = [], []
        for n, item in enumerate(itens):
            fundo = Capa(800, 420, raio=10, escurecer=True)
            fundo.definir(self.j.app.capas.capa(item))
            self.fundos.add_named(fundo, str(n))
            self.textos.add_named(self._texto(n, item), str(n))
            self.lista.pack_start(self._item_lista(n, item), False, False, 0)
        self.lista.set_visible(len(itens) > 1)
        self.show_all()
        self.lista.set_visible(len(itens) > 1)
        self._marcar()

    def _texto(self, n, item):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        caixa.set_size_request(520, -1)
        caixa.pack_start(rotulo_tecnico("Skin em destaque", f"{n + 1:02d} / {len(self.itens):02d}"),
                         False, False, 0)
        titulo = display(item.nome, "xl")
        titulo.set_max_width_chars(18)
        caixa.pack_start(titulo, False, False, 0)
        meta = [f"por {item.autor_nome}"]
        if not item.incluida:
            meta.append(f"{item.downloads} download{'' if item.downloads == 1 else 's'}")
        if item.extras.get("versao"):
            meta.append(f"v{item.extras['versao']}")
        caixa.pack_start(rotulo(" · ".join(meta), ["ms-dim"]), False, False, 0)

        acoes = Gtk.Box(spacing=10, margin_top=8)
        ver = botao("Ver a skin", "ms-primario", "ms-grande", icone_nome="go-next-symbolic", icone_depois=True,
                    ao_clicar=lambda: self.j.abrir_detalhe(item, self.itens))
        # so aqui a troca automatica para: assim da tempo de clicar
        ver.connect("enter-notify-event", lambda *_: self._pausar(True))
        ver.connect("leave-notify-event", lambda *_: self._pausar(False))
        acoes.pack_start(ver, False, False, 0)
        texto, cb, _estilo = self.j.acao_item(item)
        segundo = botao(texto, "ms-contorno", "ms-grande", ao_clicar=cb,
                        icone_nome="folder-download-symbolic" if texto == "Baixar" else None)
        segundo.set_sensitive(cb is not None)
        acoes.pack_start(segundo, False, False, 0)
        caixa.pack_start(acoes, False, False, 0)
        return caixa

    def _item_lista(self, n, item):
        b = css(Gtk.Button(relief=Gtk.ReliefStyle.NONE), "ms-vitrine-item")
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        linha = Gtk.Box(spacing=12)
        mini = Capa(64, 36, raio=4)
        mini.definir(self.j.app.capas.capa(item))
        linha.pack_start(mini, False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER)
        textos.pack_start(rotulo(item.nome, ["ms-card-nome"]), False, False, 0)
        textos.pack_start(rotulo(item.autor_nome, ["ms-pequeno"]), False, False, 0)
        linha.pack_start(textos, True, True, 0)
        caixa.pack_start(linha, False, False, 0)
        barra = Gtk.ProgressBar()
        caixa.pack_start(barra, False, False, 0)
        b.add(caixa)
        b.connect("clicked", lambda _b: self.mostrar(n))
        self.barras.append(barra)
        self.botoes.append(b)
        return b

    def mostrar(self, n):
        if not self.itens:
            return
        self.atual, self.decorrido = n % len(self.itens), 0
        self._marcar()

    def _marcar(self):
        if not self.itens:
            return
        self.fundos.set_visible_child_name(str(self.atual))
        self.textos.set_visible_child_name(str(self.atual))
        for i, (b, barra) in enumerate(zip(self.botoes, self.barras)):
            (b.get_style_context().add_class if i == self.atual else b.get_style_context().remove_class)("ms-ativo")
            barra.set_fraction(0)

    def _pausar(self, pausada):
        self.pausada = pausada
        return False

    def _passo(self):
        # fora da tela (outra pagina ou janela escondida) nao gasta nada
        if len(self.itens) < 2 or self.pausada or not self.get_mapped():
            return True
        self.decorrido += QUADRO
        self.barras[self.atual].set_fraction(min(1, self.decorrido / TEMPO))
        if self.decorrido >= TEMPO:
            self.mostrar(self.atual + 1)
        return True
