"""Janela principal: estrutura, navegação e ações."""
import subprocess
import tempfile
import threading
import traceback
import urllib.parse
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_foreign("cairo")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..aplicacao.servico_nuvem import LOCAL, PRIVADA, PUBLICA  # noqa: E402
from ..dominio.erros import Cancelado, LoginNecessario, MintSkinsErro  # noqa: E402
from ..dominio.notificacao import ACAO_ATUALIZACAO  # noqa: E402
from ..dominio.skin import EXTENSAO, EXTENSOES_ACEITAS  # noqa: E402
from . import paginas, tema  # noqa: E402
from .atualizacao import PopupAtualizacao  # noqa: E402
from .editar_perfil import ModalPerfil  # noqa: E402
from .modal import ModalAtualizar, ModalConfirmacao, ModalEscolha, ModalFormulario, ModalSenha  # noqa: E402
from .notificacoes import Sino  # noqa: E402
from . import textos as T  # noqa: E402
from .widgets import Card, Marca, avatar, botao, css, data_br, rotulo  # noqa: E402

TOPO = ["inicio", "galeria", "minhas"]          # abas no topo, como o menu do site
DETALHES = ("detalhe", "skin")                  # paginas que andam entre as skins de uma lista


class Janela(Gtk.ApplicationWindow):
    def __init__(self, gtk_app, app):
        super().__init__(application=gtk_app, title=T.APP)
        self.app = app
        css(self, "ms-janela")
        self.set_default_size(1260, 860)
        self.set_size_request(980, 640)
        self._icone()
        self.ocupado = False
        self.nova_versao = None
        self.ativa = None
        self.conta = None
        self.na_conta = {}
        self._trilha = []
        self._lista = []            # skins da lista de onde a pessoa abriu a atual (anterior / proxima)
        self._toast_id = 0
        self._toast_acao = None
        self._variante = None
        self._imagens = None
        self._logos = []
        self._estilo = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self._estilo,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.aplicar_tema()
        # janela e icones seguem o tema do sistema; ao trocar o tema, a paleta clara/escura acompanha
        Gtk.Settings.get_default().connect("notify::gtk-theme-name", lambda *_: self.aplicar_tema())
        self.app.notificacoes.ao_abrir(__version__)

        self._barra()
        raiz = Gtk.Overlay()
        self.add(raiz)
        corpo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        raiz.add(corpo)
        corpo.pack_start(self._barra_trilha(), False, False, 0)
        sobre = Gtk.Overlay()
        corpo.pack_start(sobre, True, True, 0)
        self.pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        sobre.add(self.pilha)
        self.paginas = {
            "inicio": paginas.Inicio(self), "galeria": paginas.Galeria(self),
            "minhas": paginas.Minhas(self), "conta": paginas.Conta(self),
            "preferencias": paginas.Preferencias(self), "sobre": paginas.Sobre(self),
            "detalhe": paginas.Detalhe(self), "perfil": paginas.Perfil(self),
            "skin": paginas.SkinLocal(self),
        }
        for nome, p in self.paginas.items():
            self.pilha.add_named(p.widget, nome)
        self._flutuantes(sobre)
        self.popup = PopupAtualizacao(corpo, ao_atualizar=self.atualizar_app, ao_pular=self.ignorar_versao,
                                      ao_reiniciar=self.reiniciar, ao_tentar_de_novo=self.atualizar_app,
                                      ao_fechar=lambda: self._barra_ativa(True))
        self.confirmacao = ModalConfirmacao(corpo, ao_fechar=lambda: self._barra_ativa(True))
        self.formulario = ModalFormulario(corpo, ao_fechar=lambda: self._barra_ativa(True))
        self.escolha = ModalEscolha(corpo, ao_fechar=lambda: self._barra_ativa(True))
        self.modal_atualizar = ModalAtualizar(corpo, ao_fechar=lambda: self._barra_ativa(True))
        self.modal_senha = ModalSenha(corpo, ao_fechar=lambda: self._barra_ativa(True))
        self.modal_perfil = ModalPerfil(corpo, self._salvar_perfil, ao_fechar=lambda: self._barra_ativa(True),
                                        ao_conta_no_site=self.conta_no_site)
        self._modais = [self.confirmacao, self.formulario, self.escolha, self.modal_atualizar, self.modal_senha,
                        self.modal_perfil,
                        self.popup]
        for m in self._modais:
            raiz.add_overlay(m)
        self.connect("key-press-event", self._tecla)
        self.connect("button-press-event", self._botao_mouse)
        self.connect("delete-event", self._fechando)

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._soltou)

        # a janela em si so aparece no present() do app (ao ligar o computador ela fica escondida)
        self.get_titlebar().show_all()
        self.get_child().show_all()
        self.recarregar()
        self.ir_para("inicio")
        self.set_focus(None)
        GLib.timeout_add_seconds(3, self._verificacao_automatica)
        # em segundo plano o app fica aberto por dias: confere de hora em hora (o servico limita a 12 h)
        GLib.timeout_add_seconds(3600, lambda: self._verificacao_automatica() or True)

    def _verificacao_automatica(self):
        if self.app.skins.preferencias().verificar_atualizacoes:
            self.verificar_versao(False)
        return False

    def _fechando(self, *_):
        app = self.get_application()
        if not app.em_segundo_plano():
            return False
        self.hide()
        if self.app.notificacoes.primeira_vez("segundo_plano"):
            n = Gio.Notification.new("O MintSkins continua aberto")
            n.set_body("Ele fica no ícone perto do relógio. Para sair, clique com o botão direito "
                       "no ícone e escolha “Fechar”.")
            app.send_notification("segundo-plano", n)
        return True

    def _icone(self):
        if Gtk.IconTheme.get_default().has_icon("mintskins"):
            self.set_icon_name("mintskins")
            return
        try:
            self.set_icon(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(tema.SIMBOLO), 128, 128, True))
        except GLib.Error:
            pass

    def _variante_auto(self):
        cfg = Gtk.Settings.get_default()
        if cfg.props.gtk_application_prefer_dark_theme or "dark" in (cfg.props.gtk_theme_name or "").lower():
            return "escura"
        ok, cor = Gtk.StyleContext().lookup_color("theme_bg_color")
        claridade = 0.299 * cor.red + 0.587 * cor.green + 0.114 * cor.blue if ok else 1
        return "escura" if claridade < 0.5 else "clara"

    @staticmethod
    def _botoes_com_imagem():
        """O tema desenha fechar/minimizar/maximizar com imagens (ex.: bolinhas do macOS)?"""
        caminho = Gtk.WidgetPath()
        caminho.append_type(Gtk.HeaderBar)
        caminho.iter_set_object_name(-1, "headerbar")
        caminho.append_type(Gtk.Button)
        caminho.iter_set_object_name(-1, "button")
        caminho.iter_add_class(-1, "titlebutton")
        caminho.iter_add_class(-1, "close")
        ctx = Gtk.StyleContext()
        ctx.set_path(caminho)
        fundo = ctx.get_property("background-image", Gtk.StateFlags.NORMAL)
        return isinstance(fundo, cairo.SurfacePattern)

    def aplicar_tema(self):
        escolha = self.app.skins.preferencias().aparencia
        variante = escolha if escolha in ("clara", "escura") else self._variante_auto()
        imagens = self._botoes_com_imagem()
        if (variante, imagens) != (self._variante, self._imagens):
            self._variante, self._imagens = variante, imagens
            self._estilo.load_from_data(tema.css(variante, imagens).encode())
            for logo in self._logos:
                logo.definir(tema.logo(variante))

    def logo(self, largura):
        m = Marca(tema.logo(self._variante), largura)
        self._logos.append(m)
        return m

    # ------------------------------------------------------------ barra do topo (como o menu do site)

    def _barra(self):
        hb = Gtk.HeaderBar(show_close_button=True)
        self.set_titlebar(hb)
        hb.set_custom_title(Gtk.Box())
        self.set_title(T.APP)
        marca = css(Gtk.Button(relief=Gtk.ReliefStyle.NONE, tooltip_text="Início"), "ms-logo")
        marca.add(self.logo(118))
        marca.connect("clicked", lambda _b: self.ir_para("inicio"))
        hb.pack_start(marca)

        self.abas, self.contadores = {}, {}
        primeira = None
        for pid in TOPO + [None]:          # a ultima, escondida, fica marcada fora das abas
            b = Gtk.RadioButton.new_from_widget(primeira)
            primeira = primeira or b
            b.set_mode(False)
            if pid is None:
                self._aba_nenhuma = b
                continue
            caixa = Gtk.Box(spacing=6)
            caixa.pack_start(rotulo(T.NAV[pid][1].upper(), cortar=False), False, False, 0)
            if pid == "minhas":
                self.contadores[pid] = css(Gtk.Label(label="0"), "ms-nav-contador")
                caixa.pack_start(self.contadores[pid], False, False, 0)
            b.add(caixa)
            css(b, "ms-nav")
            b.connect("toggled", self._aba_clicada, pid)
            self.abas[pid] = b
            hb.pack_start(b)

        self.conta_botao = css(Gtk.MenuButton(relief=Gtk.ReliefStyle.NONE, tooltip_text="Sua conta"),
                               "ms-conta-botao")
        hb.pack_end(self.conta_botao)
        self.sino = Sino(self.app.notificacoes, self._notificacao_clicada)
        hb.pack_end(self.sino)
        hb.pack_end(botao(T.SALVAR, "ms-primario", icone_nome="list-add-symbolic",
                          dica="Guarda o visual da tela como uma skin sua", ao_clicar=self.salvar_atual))
        hb.pack_end(botao("", "ms-fantasma", icone_nome="document-open-symbolic",
                          dica="Importar um arquivo .mintskins", ao_clicar=self.importar))
        self.btn_desfazer = botao("", "ms-fantasma", icone_nome="edit-undo-symbolic", dica=T.DESFAZER,
                                  ao_clicar=self.desfazer)
        self.btn_desfazer.set_no_show_all(True)       # so aparece quando ha uma troca para desfazer
        self.btn_desfazer.get_child().show_all()
        hb.pack_end(self.btn_desfazer)
        self._hb = hb

    def _menu_conta(self):
        """Botao da conta no canto: avatar + nome, com Conta, Preferencias, Sobre e Sair."""
        for f in self.conta_botao.get_children():
            f.destroy()
        caixa = Gtk.Box(spacing=8)
        if self.conta:
            caixa.pack_start(avatar(self.conta, pequeno=True), False, False, 0)
            caixa.pack_start(rotulo(self.conta.nome.split()[0].upper(), cortar=False), False, False, 0)
        else:
            caixa.pack_start(Gtk.Image.new_from_icon_name("avatar-default-symbolic", Gtk.IconSize.BUTTON),
                             False, False, 4)
            caixa.pack_start(rotulo("ENTRAR", cortar=False), False, False, 0)
        caixa.pack_start(Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.MENU), False, False, 0)
        self.conta_botao.add(caixa)

        pop = css(Gtk.Popover(), "ms-pop")
        menu = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        menu.set_size_request(240, -1)
        if self.conta:
            cab = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2), "ms-menu-cab")
            cab.pack_start(rotulo(self.conta.nome, ["ms-card-nome"]), False, False, 0)
            cab.pack_start(rotulo(self.conta.email, ["ms-dim", "ms-pequeno"]), False, False, 0)
            menu.pack_start(cab, False, False, 0)
            itens = [("Minha conta", lambda: self.ir_para("conta")),
                     ("Meu perfil", lambda: self.abrir_perfil(self.conta.id)),
                     ("Editar perfil", self.editar_perfil), None]
        else:
            itens = [("Entrar", lambda: self.ir_para("conta")),
                     ("Criar conta no site", lambda: self.abrir_url(f"{self.app.nuvem.site}/conta/nova")), None]
        itens += [("Preferências", lambda: self.ir_para("preferencias")), ("Sobre o MintSkins", lambda: self.ir_para("sobre"))]
        if self.conta:
            itens += [None, ("Sair da conta", self.sair, True)]
        for item in itens:
            if item is None:
                menu.pack_start(Gtk.Separator(), False, False, 0)
                continue
            texto, cb, perigo = (tuple(item) + (False,))[:3]
            b = Gtk.ModelButton(text=texto)
            if perigo:
                css(b, "ms-perigo")
            b.connect("clicked", lambda _b, cb=cb: (pop.popdown(), GLib.idle_add(cb)))
            menu.pack_start(b, False, False, 0)
        menu.show_all()
        pop.add(menu)
        self.conta_botao.set_popover(pop)
        self.conta_botao.show_all()

    def _barra_ativa(self, ativa):
        """Com um modal aberto, os botoes da barra de titulo ficam travados."""
        if ativa and any(m.aberto for m in getattr(self, "_modais", [])):
            return
        for w in self._hb.get_children():
            w.set_sensitive(ativa)
        if ativa:
            self.btn_desfazer.set_visible(self.app.skins.pode_desfazer())

    def _tecla(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            for modal in self._modais:
                if modal.aberto:
                    modal.fechar()
                    return True
            return False
        if any(m.aberto for m in self._modais) or isinstance(self.get_focus(), Gtk.Entry):
            return False
        alt = ev.state & Gdk.ModifierType.MOD1_MASK
        if alt and ev.keyval == Gdk.KEY_Left or ev.keyval == Gdk.KEY_BackSpace:
            self.voltar()
            return True
        if self.pilha.get_visible_child_name() in DETALHES and ev.keyval in (Gdk.KEY_Left, Gdk.KEY_Right):
            self.andar_na_lista(-1 if ev.keyval == Gdk.KEY_Left else 1)
            return True
        return False

    def _botao_mouse(self, _w, ev):
        if ev.button == 8:              # botao "voltar" do mouse
            self.voltar()
            return True
        return False

    def perguntar(self, titulo, texto, botao_txt, acao, icone_nome="dialog-question-symbolic", destrutivo=False):
        """Confirmacao no meio da janela, com o resto borrado."""
        self._barra_ativa(False)
        self.confirmacao.confirmar(self._variante, titulo, texto, botao_txt, acao, icone_nome, destrutivo)

    def mensagem(self, titulo, texto, icone_nome="dialog-information-symbolic", erro=False):
        self._barra_ativa(False)
        self.confirmacao.confirmar(self._variante, titulo, texto, "Entendi", None,
                                   "dialog-error-symbolic" if erro else icone_nome, destrutivo=erro, so_ok=True)

    def pedir_nome(self, titulo, botao_txt, ao_confirmar, nome="", descricao="", com_capa=False, explicacao=None):
        self._barra_ativa(False)
        self.formulario.pedir(self._variante, titulo, botao_txt, ao_confirmar, nome, descricao, com_capa,
                              explicacao)

    def _abrir_popup(self):
        self._barra_ativa(False)
        self.popup.abrir(self._variante)

    def _notificacao_clicada(self, notificacao):
        if notificacao.acao == ACAO_ATUALIZACAO:
            self.mostrar_atualizacao()

    def mostrar_atualizacao(self):
        if self.ocupado or self.popup.ocupado:
            return False
        if self.nova_versao:
            self._abrir_popup()
            self.popup.nova(self.nova_versao)
        else:
            self.verificar_versao(True)
        return False

    # ------------------------------------------------------------ trilha: voltar, onde estou, anterior/proxima

    def _barra_trilha(self):
        self.revelar_trilha = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_DOWN,
                                           transition_duration=150)
        barra = css(Gtk.Box(spacing=6), "ms-trilha-barra")
        self.btn_voltar = botao("VOLTAR", "ms-passo", icone_nome="go-previous-symbolic", dica="Voltar (Alt+←)",
                                ao_clicar=self.voltar)
        barra.pack_start(self.btn_voltar, False, False, 0)
        barra.pack_start(css(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL, margin_top=6, margin_bottom=6),
                             "ms-trilha-separador"), False, False, 6)
        self.trilha = Gtk.Box(spacing=0)
        barra.pack_start(self.trilha, True, True, 0)
        self.navegacao = Gtk.Box(spacing=2)
        self.btn_anterior = botao("ANTERIOR", "ms-passo", icone_nome="go-previous-symbolic",
                                  dica="Skin anterior (←)", ao_clicar=lambda: self.andar_na_lista(-1))
        self.posicao = rotulo("", ["ms-posicao"], cortar=False)
        self.btn_proxima = botao("PRÓXIMA", "ms-passo", icone_nome="go-next-symbolic", icone_depois=True,
                                 dica="Próxima skin (→)", ao_clicar=lambda: self.andar_na_lista(1))
        for w in (self.btn_anterior, self.posicao, self.btn_proxima):
            self.navegacao.pack_start(w, False, False, 0)
            w.show_all()
        self.navegacao.set_no_show_all(True)
        barra.pack_end(self.navegacao, False, False, 0)
        self.revelar_trilha.add(barra)
        return self.revelar_trilha

    def _aba_clicada(self, botao_, pid):
        if botao_.get_active() and not getattr(self, "_sincronizando", False):
            self.ir_para(pid)

    def ir_para(self, pagina):
        self._trilha = [("inicio", T.NAV["inicio"][1], None)]
        if pagina != "inicio":
            self._trilha.append((pagina, T.NAV[pagina][1], None))
        self._mostrar()

    def _mostrar(self):
        """Mostra o último passo da trilha e redesenha a trilha."""
        pagina, _rotulo, restaurar = self._trilha[-1]
        if restaurar:
            restaurar()
        self.pilha.set_visible_child_name(pagina)
        self.paginas[pagina].widget.get_vadjustment().set_value(0)
        raiz = next((p for p, _r, _f in reversed(self._trilha) if p in T.NAV), "inicio")
        self._sincronizando = True
        (self.abas.get(raiz) or self._aba_nenhuma).set_active(True)
        self._sincronizando = False
        self._desenhar_trilha()

    def _desenhar_trilha(self):
        for f in self.trilha.get_children():
            f.destroy()
        for i, (_pagina, rotulo_, _f) in enumerate(self._trilha):
            atual = i == len(self._trilha) - 1
            if i:
                self.trilha.pack_start(rotulo("/", ["ms-trilha-separador"]), False, False, 2)
            texto = rotulo_ if len(rotulo_) <= 32 else rotulo_[:31].rstrip() + "…"
            b = botao(texto.upper(), "ms-passo", *(["ms-passo-atual"] if atual else []),
                      ao_clicar=None if atual else (lambda n=i + 1: self._ir_trilha(n)))
            b.set_tooltip_text(rotulo_)
            self.trilha.pack_start(b, False, False, 0)
        self.trilha.show_all()
        # nas abas do topo a propria aba ja diz onde se esta; a trilha aparece ao abrir uma skin ou perfil
        self.revelar_trilha.set_reveal_child(len(self._trilha) > 2 or self._trilha[-1][0] not in T.NAV)
        self._desenhar_navegacao()

    def _desenhar_navegacao(self):
        """Anterior / 02 de 07 / Proxima, quando a skin aberta veio de uma lista."""
        pos = self._posicao_na_lista()
        mostrar = self.pilha.get_visible_child_name() in DETALHES and pos is not None and len(self._lista) > 1
        self.navegacao.set_visible(mostrar)
        if mostrar:
            self.posicao.set_text(f"{pos + 1:02d} / {len(self._lista):02d}")

    def _posicao_na_lista(self):
        atual = self.paginas[self.pilha.get_visible_child_name()]
        chave = getattr(atual, "chave", None)
        return next((i for i, (k, _o) in enumerate(self._lista) if k == chave), None) if chave else None

    def andar_na_lista(self, direcao):
        pos = self._posicao_na_lista()
        if pos is None or len(self._lista) < 2:
            return
        _chave, abrir = self._lista[(pos + direcao) % len(self._lista)]
        abrir(substituir=True)

    def _ir_trilha(self, tamanho):
        self._trilha = self._trilha[:tamanho]
        self._mostrar()

    def _empilhar(self, pagina, rotulo_, restaurar, substituir=False):
        if self._trilha and self._trilha[-1][0] == pagina or substituir:
            self._trilha.pop()
        self._trilha.append((pagina, rotulo_, restaurar))
        self._mostrar()

    def voltar(self):
        if len(self._trilha) > 1:
            self._ir_trilha(len(self._trilha) - 1)

    def _flutuantes(self, sobre):
        self.painel = Gtk.Revealer(valign=Gtk.Align.END, halign=Gtk.Align.CENTER,
                                   transition_type=Gtk.RevealerTransitionType.SLIDE_UP)
        caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "ms-flutuante")
        caixa.set_size_request(440, -1)
        linha = Gtk.Box(spacing=10)
        self.spinner = Gtk.Spinner()
        linha.pack_start(self.spinner, False, False, 0)
        self.txt_titulo = rotulo("", ["ms-card-nome"])
        linha.pack_start(self.txt_titulo, True, True, 0)
        self._cancelar_tarefa = None
        self.btn_cancelar = botao("Cancelar", "ms-fantasma", ao_clicar=lambda: self._cancelar_tarefa())
        self.btn_cancelar.set_no_show_all(True)
        linha.pack_end(self.btn_cancelar, False, False, 0)
        caixa.pack_start(linha, False, False, 0)
        self.txt_passo = rotulo("", ["ms-dim", "ms-pequeno"])
        caixa.pack_start(self.txt_passo, False, False, 0)
        self.barra = Gtk.ProgressBar()
        caixa.pack_start(self.barra, False, False, 0)
        self.painel.add(caixa)
        sobre.add_overlay(self.painel)

        self.toast = Gtk.Revealer(valign=Gtk.Align.END, halign=Gtk.Align.CENTER,
                                  transition_type=Gtk.RevealerTransitionType.SLIDE_UP)
        tc = css(Gtk.Box(spacing=14), "ms-flutuante")
        self.toast_txt = rotulo("", wrap=True)
        tc.pack_start(self.toast_txt, True, True, 0)
        self.toast_botao = css(Gtk.Button(), "ms-primario")
        self.toast_botao.connect("clicked", self._toast_clicado)
        tc.pack_start(self.toast_botao, False, False, 0)
        tc.pack_start(botao("", "ms-fantasma", icone_nome="window-close-symbolic", dica="Fechar",
                            ao_clicar=lambda: self.toast.set_reveal_child(False)), False, False, 0)
        self.toast.add(tc)
        sobre.add_overlay(self.toast)

    def recarregar(self):
        self.ativa = self.app.skins.ativa()
        self.conta = self.app.nuvem.conta()
        self.na_conta = {}
        if self.conta:
            try:
                self.na_conta = {i.id: i for i in self.app.nuvem.da_conta()}
            except MintSkinsErro:
                pass                          # sem internet: as skins aparecem como so deste computador
        self.contadores["minhas"].set_text(str(len(self.app.skins.do_usuario())))
        self.btn_desfazer.set_visible(self.app.skins.pode_desfazer())
        self._menu_conta()
        for p in self.paginas.values():
            p.atualizar()
        self._desenhar_navegacao()

    def situacao(self, skin):
        """(LOCAL | PRIVADA | PUBLICA, item da conta ou None)."""
        return self.app.nuvem.situacao(skin, self.na_conta)

    def card_local(self, skin, lista=None):
        ativa = self.ativa is not None and skin.id == self.ativa.id
        selos = [("Em uso", True)] if ativa else []
        onde, _item = self.situacao(skin)
        etiquetas = {PUBLICA: [("Pública", True)], PRIVADA: [("Privada", False)]}.get(onde, [])
        if onde != LOCAL and self.app.nuvem.pendente(skin):
            selos.append(("Mudanças não enviadas", False))
        quando = "Atualizada" if skin.foi_atualizada else "Salva"
        menu = [("Editar nome e descrição…", lambda: self.renomear(skin))]
        if ativa:
            menu.append((f"Atualizar (salvar v{skin.versao + 1})…", lambda: self.atualizar(skin)))
        menu += [("Trocar capa…", lambda: self.trocar_capa(skin)),
                 None,
                 ("Duplicar…", lambda: self.duplicar(skin)),
                 ("Exportar…", lambda: self.exportar(skin)),
                 ("Abrir pasta", lambda: self.abrir_pasta(skin.pasta)),
                 None,
                 ("Excluir…", lambda: self.excluir(skin), True)]
        principal = ("Aplicada", None, "ms-secundario") if ativa else \
            ("Aplicar", lambda: self.aplicar(skin), "ms-primario")
        return Card(self.app.capas.capa(skin), skin.nome, skin.responsavel,
                    f"v{skin.versao} · {quando.lower()} {data_br(skin.atualizado_em or skin.criado_em, hora=False)}",
                    selos, principal,
                    menu=menu, destaque=ativa, dica=skin.descricao, etiquetas=etiquetas,
                    ao_abrir=lambda: self.abrir_skin(skin, lista),
                    na_conta=(lambda: self.gerenciar_na_conta(skin=skin)) if skin.editavel else None)

    def acao_item(self, item):
        if not item.instalada:
            return "Baixar", lambda: self.baixar(item), "ms-primario"
        if self.ativa and self.ativa.id == item.skin_local:
            return "Aplicada", None, "ms-secundario"
        return "Aplicar", lambda: self.aplicar(self.app.skins.obter(item.skin_local)), "ms-primario"

    def card_item(self, item, dono=False, lista=None, so_na_conta=False):
        em_uso = bool(self.ativa and item.instalada and self.ativa.id == item.skin_local)
        selos = []
        if item.oficial:
            selos.append(("Oficial", True))
        if em_uso:
            selos.append(("Em uso", True))
        elif item.instalada and not item.incluida:
            selos.append(("Instalada", False))
        etiquetas = [("Privada", False)] if not item.publica else []
        if so_na_conta:     # em Minhas skins: esta na conta, mas nao neste computador
            selos.append(("Só na conta", False))
            etiquetas = [("Pública", True)] if item.publica else [("Privada", False)]
        na_conta = (lambda: self.gerenciar_na_conta(item=item)) if dono else None
        numeros_ = [("folder-download-symbolic", item.downloads)] if not item.incluida else []
        return Card(self.app.capas.capa(item), item.nome, item.autor_nome, "", selos,
                    self.acao_item(item), favorito=(item.favorito, lambda v: self.favoritar(item, v), item.favoritos),
                    destaque=em_uso, cadeado=item.incluida, dica=item.descricao, etiquetas=etiquetas, na_conta=na_conta,
                    numeros_=numeros_, ao_abrir=lambda: self.abrir_detalhe(item, lista),
                    ao_autor=lambda: self.abrir_perfil(item.autor_id))

    def tarefa(self, titulo, funcao, ao_terminar=None, sucesso=None, cancelar=None):
        """Roda funcao(progresso) numa thread, com o painel de progresso. Com cancelar, o painel
        mostra o botao Cancelar (a funcao para por conta propria e levanta Cancelado)."""
        if self.ocupado:
            return
        self.ocupado = True
        self.pilha.set_sensitive(False)
        self.toast.set_reveal_child(False)
        self.txt_titulo.set_text(titulo)
        self.txt_passo.set_text("Começando…")
        self.barra.set_fraction(0)
        self._cancelar_tarefa = cancelar
        self.btn_cancelar.set_visible(bool(cancelar))
        self.spinner.start()
        self.painel.set_reveal_child(True)

        def progresso(texto, fracao=None):
            def ui():
                self.txt_passo.set_text(texto)
                if fracao is not None:
                    self.barra.set_fraction(fracao)
            GLib.idle_add(ui)

        def rodar():
            try:
                res, falha = funcao(progresso), None
            except Exception as e:  # noqa: BLE001
                res, falha = None, e
                if not isinstance(e, MintSkinsErro):
                    traceback.print_exc()
            GLib.idle_add(fim, res, falha)

        def fim(res, falha):
            self.ocupado = False
            self.spinner.stop()
            self.painel.set_reveal_child(False)
            self.pilha.set_sensitive(True)
            self.recarregar()
            if isinstance(falha, Cancelado):
                return
            if falha:
                self._erro(titulo, falha)
                return
            if ao_terminar:
                ao_terminar(res)
            if sucesso:
                self.avisar(sucesso if isinstance(sucesso, str) else sucesso(res))

        threading.Thread(target=rodar, daemon=True).start()

    def _erro(self, titulo, falha):
        if isinstance(falha, LoginNecessario):
            self.avisar(str(falha), "Entrar", lambda: self.ir_para("conta"))
        else:
            self.mensagem(f"{titulo}: não deu certo", str(falha), erro=True)

    def _rapido(self, titulo, funcao, sucesso=None):
        try:
            res = funcao()
        except MintSkinsErro as e:
            self._erro(titulo, e)
            return None
        self.recarregar()
        if sucesso:
            self.avisar(sucesso)
        return res

    def avisar(self, texto, botao_txt=None, acao=None, segundos=6):
        self.toast_txt.set_text(texto)
        self._toast_acao = acao
        self.toast_botao.set_visible(bool(botao_txt))
        if botao_txt:
            self.toast_botao.set_label(botao_txt)
        self.toast.set_reveal_child(True)
        self._toast_id += 1
        meu = self._toast_id

        def esconder():
            if meu == self._toast_id:
                self.toast.set_reveal_child(False)
            return False
        GLib.timeout_add_seconds(segundos, esconder)

    def _toast_clicado(self, _b):
        self.toast.set_reveal_child(False)
        if self._toast_acao:
            self._toast_acao()

    def _com_foto(self, usar, continuar):
        if not usar:
            continuar(None)
            return
        arq = Path(tempfile.mkstemp(prefix="mintskins-capa-", suffix=".png")[1])
        self.iconify()

        def tirar():
            ok = self.app.capas.capturar_tela(arq)
            self.deiconify()
            self.present()
            continuar(arq if ok else None)
            return False
        GLib.timeout_add(900, tirar)

    def aplicar(self, skin, sem_backup=False):
        if not sem_backup and self.app.skins.precisa_backup():
            # o visual da tela nao e nenhuma skin: oferece salvar antes, mas a pessoa decide
            self._barra_ativa(False)
            self.escolha.escolher(self._variante, "Salvar o visual atual antes?",
                                  "O visual que está na tela agora ainda não é uma skin. Se salvar, você pode "
                                  "voltar a ele quando quiser. Sem salvar, só o Desfazer da última troca volta.", [
                                      ("salvar", "document-save-symbolic", "Salvar e aplicar",
                                       "Guarda o visual atual como uma skin sua e depois troca."),
                                      ("aplicar", "go-next-symbolic", "Aplicar sem salvar",
                                       f"Troca direto para “{skin.nome}”."),
                                  ], lambda c: self.salvar_atual(primeiro_backup=True,
                                                                 depois=lambda: self.aplicar(skin, True))
                                  if c == "salvar" else self.aplicar(skin, True))
            return
        prefs = self.app.skins.preferencias()
        self.tarefa(f"Aplicando “{skin.nome}”",
                    lambda prog: self.app.skins.aplicar(skin, prefs, prog, sem_backup=sem_backup),
                    ao_terminar=lambda r: self.avisar(
                        f"“{skin.nome}” aplicada." + "".join(f" {a[:1].upper()}{a[1:]}." for a in r.avisos),
                        "Desfazer", self.desfazer, segundos=10))

    def desfazer(self):
        if self.ocupado or not self.app.skins.pode_desfazer():
            return
        nome = self.app.skins.nome_antes_da_troca()
        texto = (f"O desktop volta para “{nome}”, o visual de antes da última troca."
                 if nome else "O desktop volta ao visual que estava antes da última troca.")
        self.perguntar("Desfazer a última troca?", texto + " Você pode desfazer de novo depois.",
                       "Desfazer", self._desfazer_confirmado, icone_nome="edit-undo-symbolic")

    def _desfazer_confirmado(self):
        prefs = self.app.skins.preferencias()
        self.tarefa("Voltando ao visual anterior", lambda prog: self.app.skins.desfazer(prefs, prog),
                    sucesso="Visual anterior restaurado.")

    def salvar_atual(self, primeiro_backup=False, depois=None):
        """Com uma skin sua em uso, pergunta se atualiza ela (nova versao) ou cria outra."""
        ativa = self.ativa
        if not primeiro_backup and ativa and ativa.editavel:
            self._barra_ativa(False)
            self.escolha.escolher(self._variante, "Salvar skin", "Você está usando "
                                  f"“{ativa.nome}”. Quer guardar as mudanças nela ou criar outra skin?", [
                                      ("atualizar", "view-refresh-symbolic", f"Atualizar “{ativa.nome}”",
                                       f"Salva por cima e vira a v{ativa.versao + 1}."),
                                      ("nova", "list-add-symbolic", "Nova skin",
                                       "Cria outra skin com o visual da tela; a atual não muda."),
                                  ], lambda c: self.atualizar(ativa) if c == "atualizar" else self._salvar_nova())
            return
        self._salvar_nova(primeiro_backup, depois)

    def _salvar_nova(self, primeiro_backup=False, depois=None):
        def salvar(nome, desc, foto):
            self._com_foto(foto, lambda capa: self.tarefa(
                f"Salvando “{nome}”", lambda prog: self.app.skins.salvar_atual(nome, desc, capa, prog),
                ao_terminar=lambda _s: depois and GLib.idle_add(depois),
                sucesso=lambda s: f"“{s.nome}” salva em Minhas skins."))
        if primeiro_backup:
            self.pedir_nome("Salve seu visual primeiro", "Salvar", salvar, "Meu visual original", com_capa=True,
                            explicacao="Antes da primeira troca, guarde o visual atual como uma skin sua. "
                                       "Assim você sempre pode voltar a ele.")
        else:
            self.pedir_nome("Nova skin", "Salvar", salvar, com_capa=True,
                            explicacao="Guarda tudo o que está na tela agora: tema, ícones, painel, dock e "
                                       "papel de parede.")

    def atualizar(self, skin):
        """Grava a tela por cima da skin (v+1), escolhendo a capa e, se ela esta na conta, enviando junto."""
        onde, _item = self.situacao(skin)
        self._barra_ativa(False)
        self.modal_atualizar.pedir(self._variante, skin, onde != LOCAL,
                                   lambda capa, enviar: self._atualizar(skin, capa, enviar, onde))

    def _atualizar(self, skin, capa, enviar, onde):
        nova = skin.versao + 1

        def gravar(arquivo):
            def rodar(prog):
                s = self.app.skins.atualizar_com_atual(skin, arquivo, prog)
                if enviar:
                    prog("Enviando a versão nova para a conta", 0.9)
                    self.app.nuvem.enviar(s, onde == PUBLICA)
                return s
            self.tarefa(f"Salvando “{skin.nome}” v{nova}", rodar,
                        sucesso=f"“{skin.nome}” v{nova} salva" + (" e enviada para a conta." if enviar else "."))
        if capa == "imagem":
            arquivo = self._escolher_imagem()
            if arquivo:
                gravar(arquivo)
        else:
            self._com_foto(capa == "tela", gravar)

    def renomear(self, skin):
        self.pedir_nome("Editar nome e descrição", "Salvar", lambda nome, desc, _f: self._rapido(
            "Editar", lambda: self.app.skins.editar(skin, nome, desc), "Alterações salvas."),
            skin.nome, skin.descricao)

    def duplicar(self, skin):
        self.pedir_nome("Duplicar", "Duplicar", lambda nome, desc, _f: self.tarefa(
            "Duplicando", lambda _p: self.app.skins.duplicar(skin, nome, desc),
            sucesso=lambda s: f"“{s.nome}” criada em Minhas skins."),
            f"{skin.nome} (cópia)", skin.descricao)

    def excluir(self, skin):
        texto = "A skin sai deste computador. O visual da tela não muda."
        if self.situacao(skin)[0] != LOCAL:
            texto += " A cópia na sua conta continua lá."
        self.perguntar(f"Excluir “{skin.nome}”?", texto, "Excluir",
                       lambda: self._rapido("Excluir", lambda: self.app.skins.excluir(skin), f"“{skin.nome}” excluída."),
                       icone_nome="user-trash-symbolic", destrutivo=True)

    def _escolher_imagem(self):
        """Abre o seletor de imagem e devolve um PNG temporario (ate 1280 px), ou None."""
        d = Gtk.FileChooserNative(title="Escolha a capa", transient_for=self,
                                  action=Gtk.FileChooserAction.OPEN, accept_label="Usar")
        f = Gtk.FileFilter()
        f.set_name("Imagens")
        f.add_pixbuf_formats()
        d.add_filter(f)
        tmp = None
        if d.run() == Gtk.ResponseType.ACCEPT:
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(d.get_filename(), 1280, -1, True)
                tmp = Path(tempfile.mkstemp(prefix="mintskins-capa-", suffix=".png")[1])
                pix.savev(str(tmp), "png", [], [])
            except GLib.Error as e:
                self.mensagem("Imagem inválida", str(e), erro=True)
        d.destroy()
        return tmp

    def trocar_capa(self, skin):
        """So a capa muda (a versao continua a mesma). Com a skin em uso, da para usar uma foto da tela."""
        def usar(arquivo):
            if arquivo:
                self._rapido("Trocar capa", lambda: self.app.skins.trocar_capa(skin, arquivo), "Capa trocada.")
                Path(arquivo).unlink(missing_ok=True)
        if not (self.ativa and self.ativa.id == skin.id):
            usar(self._escolher_imagem())
            return
        self._barra_ativa(False)
        self.escolha.escolher(self._variante, "Trocar a capa", f"A nova capa de “{skin.nome}”:", [
            ("tela", "camera-photo-symbolic", "Foto da tela", "Tira uma foto do desktop agora."),
            ("imagem", "image-x-generic-symbolic", "Escolher imagem", "Usa uma imagem do seu computador."),
        ], lambda c: self._com_foto(True, usar) if c == "tela" else usar(self._escolher_imagem()))

    def exportar(self, skin):
        d = Gtk.FileChooserNative(title="Exportar", transient_for=self,
                                  action=Gtk.FileChooserAction.SAVE, accept_label="Exportar")
        d.set_current_name(f"{skin.id}{EXTENSAO}")
        d.set_do_overwrite_confirmation(True)
        if d.run() == Gtk.ResponseType.ACCEPT:
            destino = d.get_filename()
            self.tarefa("Exportando", lambda _p: self.app.skins.exportar(skin, destino),
                        sucesso=lambda arq: f"Exportada para {arq.replace(str(Path.home()), '~')}")
        d.destroy()

    def importar(self, pasta=False):
        d = Gtk.FileChooserNative(
            title="Importar", transient_for=self, accept_label="Importar",
            action=Gtk.FileChooserAction.SELECT_FOLDER if pasta else Gtk.FileChooserAction.OPEN)
        if not pasta:
            f = Gtk.FileFilter()
            f.set_name("Skins do MintSkins")
            for ext in EXTENSOES_ACEITAS:
                f.add_pattern("*" + ext)
            f.add_pattern("*.tar.gz")
            d.add_filter(f)
        if d.run() == Gtk.ResponseType.ACCEPT:
            self.importar_arquivo(d.get_filename())
        d.destroy()

    def importar_arquivo(self, caminho):
        self.tarefa("Importando", lambda _p: self.app.skins.importar(caminho),
                    sucesso=lambda s: f"“{s.nome}” importada.")

    def _soltou(self, _w, _ctx, _x, _y, dados, _info, _t):
        for uri in dados.get_uris() or []:
            p = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
            if Path(p).exists():
                self.importar_arquivo(p)
                break

    def _definir_lista(self, lista, tipo):
        """Guarda a lista de onde a skin foi aberta, para andar com Anterior / Proxima."""
        if lista is None:
            return
        if tipo == "item":
            self._lista = [(f"item:{i.id}", lambda substituir=False, i=i: self.abrir_detalhe(i, substituir=substituir))
                           for i in lista]
        else:
            self._lista = [(f"skin:{s.id}", lambda substituir=False, s=s: self.abrir_skin(s, substituir=substituir))
                           for s in lista]

    def abrir_detalhe(self, item, lista=None, substituir=False):
        self._definir_lista(lista, "item")
        self._empilhar("detalhe", item.nome, lambda: self.paginas["detalhe"].mostrar(item), substituir)

    def abrir_skin(self, skin, lista=None, substituir=False):
        """Pagina de uma skin deste computador: aplicar, editar, publicar, atualizar na conta."""
        self._definir_lista(lista, "skin")
        self._empilhar("skin", skin.nome, lambda: self.paginas["skin"].mostrar(skin), substituir)

    def abrir_perfil(self, autor_id):
        perfil = self.app.nuvem.perfil(autor_id)
        if not perfil:
            self.avisar("Perfil não encontrado.")
            return
        self._empilhar("perfil", perfil.nome, lambda: self.paginas["perfil"].mostrar(perfil))

    def favoritar(self, item, favorito):
        self._rapido("Favoritar", lambda: self.app.nuvem.favoritar(item, favorito))

    def baixar(self, item):
        self.tarefa(f"Baixando “{item.nome}”", lambda _p: self.app.nuvem.baixar(item),
                    ao_terminar=lambda s: self.avisar(f"“{s.nome}” está em Minhas skins.", "Aplicar",
                                                      lambda: self.aplicar(s)))

    def _exigir_conta(self, texto):
        if self.conta:
            return True
        self.avisar(texto, "Entrar", lambda: self.ir_para("conta"))
        return False

    def enviar(self, skin):
        self.gerenciar_na_conta(skin=skin)

    def limites(self):
        """{PUBLICA: (usadas, maximo), PRIVADA: (...)}; maximo None = sem limite. Usadas vem da conta."""
        itens = list(self.na_conta.values())
        usadas = {PUBLICA: sum(1 for i in itens if i.publica), PRIVADA: sum(1 for i in itens if not i.publica)}
        do_site = (self.conta.limites if self.conta else None) or {}
        maximo = {PUBLICA: (do_site.get("publicas") or {}).get("maximo", 5),
                  PRIVADA: (do_site.get("privadas") or {}).get("maximo", 5)}
        if not do_site:
            maximo = {PUBLICA: 5, PRIVADA: 5}        # site antigo: o limite padrao dos membros
        return {k: (usadas[k], maximo[k]) for k in (PUBLICA, PRIVADA)}

    def cheio(self, destino):
        usadas, maximo = self.limites()[destino]
        return maximo is not None and usadas >= maximo

    def uso(self, destino):
        usadas, maximo = self.limites()[destino]
        return f"{usadas}/{maximo}" if maximo is not None else str(usadas)

    def gerenciar_na_conta(self, skin=None, item=None):
        """Modal com o que da para fazer na conta: guardar, publicar, despublicar ou remover."""
        if not self._exigir_conta("Entre na sua conta para guardar ou publicar skins."):
            return
        if skin is not None:
            onde, item = self.situacao(skin)
        else:
            onde = PUBLICA if item.publica else PRIVADA
        nome = (skin or item).nome
        pub, priv = self.uso(PUBLICA), self.uso(PRIVADA)
        cheia = {PUBLICA: "Limite de publicadas atingido.", PRIVADA: "Limite de guardadas atingido."}
        guardar = (PRIVADA, "changes-prevent-symbolic", "Guardar na conta",
                   f"Privada, só você vê. Guardadas: {priv}." + (f" {cheia[PRIVADA]}" if self.cheio(PRIVADA) else ""),
                   self.cheio(PRIVADA))
        publicar = (PUBLICA, "web-browser-symbolic", "Publicar na galeria",
                    f"Todo mundo vê e pode baixar. Publicadas: {pub}." +
                    (f" {cheia[PUBLICA]}" if self.cheio(PUBLICA) else ""), self.cheio(PUBLICA))
        despublicar = (PRIVADA, "changes-prevent-symbolic", "Deixar privada",
                       f"Sai da galeria e fica privada na conta. Guardadas: {priv}." +
                       (f" {cheia[PRIVADA]}" if self.cheio(PRIVADA) else ""), self.cheio(PRIVADA))
        remover = ("remover", "user-trash-symbolic", "Remover da conta",
                   "Sai da conta e da galeria. Você escolhe se fica neste computador.")
        opcoes = {LOCAL: [guardar, publicar], PRIVADA: [publicar, remover], PUBLICA: [despublicar, remover]}[onde]
        estado = {LOCAL: "Está só neste computador.", PRIVADA: "Está guardada na conta (privada).",
                  PUBLICA: "Está publicada na galeria."}[onde]

        def escolheu(c):
            if c == "remover":
                self.remover_da_conta(item, skin)
            elif skin is not None:
                self.mudar_situacao(skin, c)
            else:
                self.tornar_publica(item, c == PUBLICA)
        self._barra_ativa(False)
        self.escolha.escolher(self._variante, f"“{nome}” na sua conta",
                              f"{estado} Sua conta: {pub} publicadas · {priv} guardadas.", opcoes, escolheu)

    def mudar_situacao(self, skin, destino):
        """Leva a skin para LOCAL, PRIVADA ou PUBLICA, fazendo o que precisar (enviar, publicar, remover)."""
        atual, item = self.situacao(skin)
        if destino == atual:
            return
        if destino != LOCAL and not self._exigir_conta("Entre na sua conta para guardar ou publicar skins."):
            return
        if destino == LOCAL:
            self.remover_da_conta(item, skin)
        elif destino != atual and self.cheio(destino):
            self.mensagem("Limite da conta", f"Você já tem {self.uso(destino)} skins "
                          f"{'publicadas' if destino == PUBLICA else 'guardadas'}. Mude ou remova outra antes.")
        elif atual == LOCAL:
            publica = destino == PUBLICA

            def enviar():
                self.tarefa(f"Enviando “{skin.nome}”", lambda _p: self.app.nuvem.enviar(skin, publica),
                            sucesso="Publicada na galeria." if publica else "Guardada na sua conta, só você vê.")
            if publica:
                self.perguntar(f"Publicar “{skin.nome}”?", "Ela vai para a sua conta e aparece na galeria do app "
                               "e do site. Qualquer pessoa pode ver, baixar e favoritar.", "Publicar", enviar,
                               icone_nome="web-browser-symbolic")
            else:
                enviar()
        else:
            self.tornar_publica(item, destino == PUBLICA)

    def enviar_atualizacao(self, skin):
        """Manda a versao deste computador para a conta (vira uma versao nova no site)."""
        onde, _item = self.situacao(skin)
        if onde == LOCAL:
            self.enviar(skin)
            return
        self.tarefa(f"Enviando a atualização de “{skin.nome}”",
                    lambda _p: self.app.nuvem.enviar(skin, onde == PUBLICA),
                    sucesso="Atualização enviada. O site já mostra a versão nova.")

    def tornar_publica(self, item, publica):
        destino = PUBLICA if publica else PRIVADA
        if self.cheio(destino):
            self.mensagem("Limite da conta", f"Você já tem {self.uso(destino)} skins "
                          f"{'publicadas' if publica else 'guardadas'}. Mude ou remova outra antes.")
            return
        if publica:
            self.perguntar(f"Publicar “{item.nome}”?", "Ela aparece na galeria do app e do site. Qualquer "
                           "pessoa pode ver, baixar e favoritar.", "Publicar",
                           lambda: self._rapido("Publicar", lambda: self.app.nuvem.definir_publica(item, True),
                                                "Publicada na galeria."),
                           icone_nome="web-browser-symbolic")
        else:
            self.perguntar(f"Deixar “{item.nome}” privada?", "Ela sai da galeria do app e do site e continua "
                           "na sua conta. Só você vê e pode baixar.", "Deixar privada",
                           lambda: self._rapido("Deixar privada", lambda: self.app.nuvem.definir_publica(item, False),
                                                "Agora só você vê esta skin."),
                           icone_nome="changes-prevent-symbolic")

    def remover_da_conta(self, item, skin=None):
        """Tira da conta confirmando com a senha. Pergunta antes se a skin fica neste computador:
        se nao estiver aqui, baixa antes; "apagar de vez" tira daqui tambem."""
        local = skin or next((s for s in self.app.skins.do_usuario()
                              if item.id in (s.extras.get("nuvem_id"), s.extras.get("galeria_id"))), None)

        def com_senha(apagar_daqui):
            def confirmar(senha):
                try:
                    pagina = self.app.nuvem.remover(item, senha)
                except MintSkinsErro as e:
                    return str(e)              # senha errada: o modal mostra e deixa tentar de novo
                if pagina:                     # conta sem senha (so Google/GitHub): o site confirma por codigo
                    self.abrir_url(pagina)
                    self.avisar("Digite no site o código que enviamos para o seu e-mail para confirmar.")
                    return None
                if apagar_daqui and local and local.editavel:
                    self.app.skins.excluir(local)
                GLib.idle_add(lambda: self.recarregar() or False)
                self.avisar(f"“{item.nome}” saiu da sua conta" +
                            (" e deste computador." if apagar_daqui and local else "."))
                return None
            self._barra_ativa(False)
            self.modal_senha.pedir(self._variante, f"Remover “{item.nome}” da conta",
                                   "Ela sai da sua conta e da galeria" +
                                   (" e é apagada deste computador." if apagar_daqui and local else
                                    "; a cópia neste computador continua.") + " Para confirmar, digite a sua senha.",
                                   "Apagar de vez" if apagar_daqui else "Remover da conta", confirmar)

        def escolheu(c):
            if c == "apagar" or local:
                com_senha(c == "apagar")
            else:
                self.tarefa(f"Baixando “{item.nome}”", lambda _p: self.app.nuvem.baixar(item),
                            ao_terminar=lambda _s: com_senha(False))
        manter = ("Manter neste computador", "Sai da conta e da galeria. A cópia daqui continua sua.") if local \
            else ("Salvar neste computador", "Baixa para cá antes e depois tira da conta.")
        self._barra_ativa(False)
        self.escolha.escolher(self._variante, f"Remover “{item.nome}” da conta?",
                              "Depois de escolher, confirme com a senha da sua conta.", [
                                  ("manter", "computer-symbolic", *manter),
                                  ("apagar", "user-trash-symbolic", "Apagar de vez",
                                   "Sai da conta, da galeria" + (" e deste computador." if local else ".") +
                                   " Não dá para desfazer."),
                              ], escolheu)

    def copiar_link(self, url):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(url, -1)
        self.avisar("Link copiado.")

    def entrar(self, criar, dados, erro):
        try:
            self.app.nuvem.entrar(dados["email"], dados["senha"])
        except MintSkinsErro as e:
            erro.set_text(str(e))
            erro.show()
            return
        self.recarregar()
        self.avisar(f"Olá, {self.conta.nome.split()[0]}!")

    def entrar_pelo_navegador(self, provedor=""):
        """Google, GitHub (ou senha no site): a pessoa termina no navegador e volta para o app."""
        nome = {"google_oauth2": "Google", "github": "GitHub"}.get(provedor, "o navegador")
        cancelou = threading.Event()

        def rodar(progresso):
            progresso("Termine de entrar no navegador. Esta janela espera você voltar.")
            return self.app.nuvem.entrar_pelo_navegador(lambda url: GLib.idle_add(self.abrir_url, url),
                                                        provedor, cancelou.is_set)

        def entrou(conta):
            self.present()
            self.avisar(f"Olá, {conta.nome.split()[0]}!")
        self.tarefa(f"Entrando com {nome}", rodar, ao_terminar=entrou, cancelar=cancelou.set)

    def editar_perfil(self):
        if not self.conta:
            self.ir_para("conta")
            return
        self._barra_ativa(False)
        self.modal_perfil.editar(self._variante, self.conta)

    def _salvar_perfil(self, d):
        """Chamado pelo modal. Devolve o texto do erro, ou None se salvou. O e-mail nao muda aqui."""
        nuvem = self.app.nuvem
        try:
            nuvem.atualizar_perfil(d["nome"], self.conta.email, d["bio"], d["links"])
            if d["foto_nova"]:
                nuvem.definir_foto(d["foto_nova"])
            elif d["remover_foto"]:
                nuvem.definir_foto(None)
        except MintSkinsErro as e:
            return str(e)
        finally:
            if d["foto_nova"]:
                Path(d["foto_nova"]).unlink(missing_ok=True)
        self.recarregar()
        self.avisar("Perfil atualizado.")
        return None

    def conta_no_site(self):
        """E-mail, senha, logins sociais, computadores e excluir a conta: tudo pelo site."""
        self.abrir_url(f"{self.app.nuvem.site}/conta/editar")

    def ver_perfil(self, perfil_ou_conta):
        self.abrir_url(getattr(perfil_ou_conta, "pagina", "") or f"{self.app.nuvem.site}/u/{perfil_ou_conta.id}")

    def sair(self):
        self.app.nuvem.sair()
        self.recarregar()
        self.avisar("Você saiu da conta.")

    def verificar_versao(self, manual):
        """Automatica: so aparece se houver versao nova. Manual: o popup mostra a busca."""
        if manual:
            if self.ocupado:
                return
            self._abrir_popup()
            self.popup.verificando()

        def depois(nova, falha):
            self.nova_versao = nova
            if nova:
                self.app.notificacoes.versao_disponivel(nova.versao)
                self.sino.atualizar()
            if self.ocupado or self.popup.ocupado:
                return
            if nova and not self.get_visible():      # em segundo plano: avisa pelo sistema
                n = Gio.Notification.new(f"MintSkins {nova.versao} disponível")
                n.set_body("Clique para ver as novidades e atualizar.")
                n.set_default_action("app.atualizacao")
                self.get_application().send_notification("atualizacao", n)
                return
            if nova:
                self._abrir_popup()
                self.popup.nova(nova)
            elif manual and falha:
                self.popup.erro(falha)
            elif manual:
                self.popup.sem_novidade()

        def rodar():
            nova, falha = None, None
            try:
                nova = self.app.atualizacoes.verificar(forcar=manual)
            except MintSkinsErro as e:
                falha = str(e)
            GLib.idle_add(depois, nova, falha)
        threading.Thread(target=rodar, daemon=True).start()

    def atualizar_app(self):
        """Baixa e instala a versao nova sem sair do app."""
        nova = self.nova_versao
        if not nova:
            self.verificar_versao(True)
            return
        if self.ocupado:
            return
        self.ocupado = True
        self._abrir_popup()
        self.popup.baixando(nova.versao)

        def ao_baixar(baixados, total):
            GLib.idle_add(self.popup.baixando, nova.versao, baixados, total)

        def rodar():
            falha = None
            try:
                self.app.atualizacoes.atualizar(
                    nova, ao_baixar, lambda: GLib.idle_add(self.popup.instalando, nova.versao))
            except Exception as e:  # noqa: BLE001
                falha = e
                if not isinstance(e, MintSkinsErro):
                    traceback.print_exc()
            GLib.idle_add(fim, falha)

        def fim(falha):
            self.ocupado = False
            if falha:
                self.popup.erro(str(falha) if isinstance(falha, MintSkinsErro)
                                else "A conexão falhou no meio do download. Tente de novo.")
                return
            self.app.notificacoes.remover(f"versao:{nova.versao}")
            self.app.notificacoes.adicionar(f"pronta:{nova.versao}", f"MintSkins {nova.versao} instalado",
                                            "Reinicie o MintSkins para usar a versão nova.", "sucesso")
            self.sino.atualizar()
            self.popup.pronto(nova.versao)

        threading.Thread(target=rodar, daemon=True).start()

    def ignorar_versao(self):
        if self.nova_versao:
            self.app.atualizacoes.ignorar(self.nova_versao)
            self.app.notificacoes.remover(f"versao:{self.nova_versao.versao}")
            self.sino.atualizar()
        self.nova_versao = None
        self.popup.fechar()

    def reiniciar(self):
        subprocess.Popen(["sh", "-c", "sleep 1; exec mintskins"], start_new_session=True)
        self.get_application().quit()

    def mudar_preferencia(self, campo, valor):
        prefs = self.app.skins.preferencias()
        setattr(prefs, campo, valor)
        self.app.skins.gravar_preferencias(prefs)

    def mudar_inicio_automatico(self, ativo):
        self.mudar_preferencia("iniciar_com_sistema", ativo)
        try:
            self.app.inicio_automatico.definir(ativo)
        except OSError as e:
            self.mensagem("Iniciar com o sistema", str(e), erro=True)

    def mudar_segundo_plano(self, ativo):
        self.mudar_preferencia("segundo_plano", ativo)
        self.get_application().mostrar_bandeja(ativo)

    def mudar_aparencia(self, aparencia):
        self.mudar_preferencia("aparencia", aparencia or "auto")
        self.aplicar_tema()

    def restaurar_login(self):
        self.tarefa("Restaurando a tela de login", lambda _p: self.app.skins.restaurar_tela_login(),
                    sucesso="Tela de login original restaurada.")

    def abrir_pasta(self, pasta):
        Path(pasta).mkdir(parents=True, exist_ok=True)
        Gio.AppInfo.launch_default_for_uri(Path(pasta).as_uri(), None)

    def abrir_url(self, url):
        Gtk.show_uri_on_window(self, url, Gdk.CURRENT_TIME)
