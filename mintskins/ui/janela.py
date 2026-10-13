"""Janela principal: estrutura, navegação e ações."""
import subprocess
import tempfile
import threading
import traceback
import urllib.parse
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

from .. import __version__  # noqa: E402
from ..dominio.erros import LoginNecessario, MintSkinsErro  # noqa: E402
from ..dominio.skin import EXTENSAO, EXTENSOES_ACEITAS  # noqa: E402
from . import dialogos, paginas, tema  # noqa: E402
from . import textos as T  # noqa: E402
from .widgets import Avatar, Card, Marca, botao, css, data_br, icone, rotulo  # noqa: E402

LATERAL = [("inicio", "SKINS"), ("galeria", "SKINS"), ("minhas", "SKINS"),
           ("conta", "MINTSKINS"), ("preferencias", "MINTSKINS"), ("sobre", "MINTSKINS")]


class Janela(Gtk.ApplicationWindow):
    def __init__(self, gtk_app, app):
        super().__init__(application=gtk_app, title=T.APP)
        self.app = app
        css(self, "ms-janela")
        self.set_default_size(1220, 840)
        self.set_size_request(940, 620)
        self._icone()
        self.ocupado = False
        self.nova_versao = None
        self.ativa = None
        self.conta = None
        self._trilha = []
        self._toast_id = 0
        self._toast_acao = None
        self._variante = None
        self._logos = []
        self._estilo = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self._estilo,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.aplicar_tema()

        self._barra()
        corpo = Gtk.Box()
        self.add(corpo)
        corpo.pack_start(self._lateral(), False, False, 0)
        sobre = Gtk.Overlay()
        corpo.pack_start(sobre, True, True, 0)
        self.pilha = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=150)
        sobre.add(self.pilha)
        self.paginas = {
            "inicio": paginas.Inicio(self), "galeria": paginas.Galeria(self),
            "minhas": paginas.Minhas(self), "conta": paginas.Conta(self),
            "preferencias": paginas.Preferencias(self), "sobre": paginas.Sobre(self),
            "detalhe": paginas.Detalhe(self), "perfil": paginas.Perfil(self),
        }
        for nome, p in self.paginas.items():
            self.pilha.add_named(p.widget, nome)
        self._flutuantes(sobre)

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self._soltou)
        Gtk.Settings.get_default().connect("notify::gtk-theme-name", lambda *_: self.aplicar_tema())

        self.show_all()
        self.recarregar()
        self.ir_para("inicio")
        self.set_focus(None)
        if self.app.skins.preferencias().verificar_atualizacoes:
            GLib.timeout_add_seconds(3, lambda: self.verificar_versao(False) and False)

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

    def aplicar_tema(self):
        escolha = self.app.skins.preferencias().aparencia
        variante = escolha if escolha in ("clara", "escura") else self._variante_auto()
        if variante != self._variante:
            self._variante = variante
            self._estilo.load_from_data(tema.css(variante).encode())
            for logo in self._logos:
                logo.definir(tema.logo(variante))

    def logo(self, largura):
        m = Marca(tema.logo(self._variante), largura)
        self._logos.append(m)
        return m

    def _barra(self):
        hb = Gtk.HeaderBar(show_close_button=True)
        self.set_titlebar(hb)
        hb.set_custom_title(Gtk.Box())
        self.set_title(T.APP)
        self.btn_voltar = botao("", "ms-fantasma", icone_nome="go-previous-symbolic", dica="Voltar",
                                ao_clicar=self.voltar)
        hb.pack_start(self.btn_voltar)
        self.trilha = css(Gtk.Box(spacing=4), "ms-trilha")
        hb.pack_start(self.trilha)
        hb.pack_end(botao(T.SALVAR, "ms-primario", icone_nome="list-add-symbolic",
                          dica="Guarda o visual da tela como uma skin sua", ao_clicar=self.salvar_atual))
        hb.pack_end(botao("Importar", "ms-fantasma", icone_nome="document-open-symbolic",
                          dica="Importar um arquivo .mintskins", ao_clicar=self.importar))
        self.btn_desfazer = botao("", "ms-fantasma", icone_nome="edit-undo-symbolic", dica=T.DESFAZER,
                                  ao_clicar=self.desfazer)
        hb.pack_end(self.btn_desfazer)

    def _lateral(self):
        lateral = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "ms-lateral")
        lateral.set_size_request(250, -1)
        logo = self.logo(170)
        logo.set_halign(Gtk.Align.START)
        logo.set_margin_start(22)
        logo.set_margin_top(20)
        logo.set_margin_bottom(10)
        lateral.pack_start(logo, False, False, 0)

        self.nav = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.nav.set_header_func(self._grupo_nav)
        self.contadores = {}
        for pid, grupo in LATERAL:
            icn, titulo = T.NAV[pid]
            linha = Gtk.ListBoxRow()
            linha.pagina, linha.grupo = pid, grupo
            caixa = Gtk.Box(spacing=12)
            caixa.pack_start(icone(icn, Gtk.IconSize.BUTTON), False, False, 0)
            caixa.pack_start(rotulo(titulo), True, True, 0)
            if pid in ("galeria", "minhas"):
                self.contadores[pid] = css(Gtk.Label(label="0"), "ms-contador")
                caixa.pack_end(self.contadores[pid], False, False, 0)
            linha.add(caixa)
            self.nav.add(linha)
        self.nav.connect("row-selected", self._navegou)
        lateral.pack_start(self.nav, False, False, 0)

        self.rodape = Gtk.Box(spacing=10, margin=14)
        lateral.pack_end(self.rodape, False, False, 0)
        return lateral

    def _rodape(self):
        for f in self.rodape.get_children():
            f.destroy()
        b = css(Gtk.Button(relief=Gtk.ReliefStyle.NONE), "ms-fantasma")
        caixa = Gtk.Box(spacing=10)
        if self.conta:
            caixa.pack_start(Avatar(self.conta.iniciais), False, False, 0)
            caixa.pack_start(rotulo(self.conta.nome, ["ms-card-nome"]), True, True, 0)
        else:
            caixa.pack_start(icone("avatar-default-symbolic", Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            caixa.pack_start(rotulo("Entrar", ["ms-card-nome"]), True, True, 0)
        b.add(caixa)
        b.connect("clicked", lambda _b: self.ir_para("conta"))
        self.rodape.pack_start(b, True, True, 0)
        self.rodape.show_all()

    @staticmethod
    def _grupo_nav(linha, antes):
        novo = antes is None or antes.grupo != linha.grupo
        linha.set_header(rotulo(linha.grupo, ["ms-rotulo-grupo"]) if novo else None)

    def _navegou(self, _lista, linha):
        if linha is None or getattr(self, "_sincronizando", False):
            return
        self._trilha = [("inicio", T.NAV["inicio"][1], None)]
        if linha.pagina != "inicio":
            self._trilha.append((linha.pagina, T.NAV[linha.pagina][1], None))
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
        for linha in self.nav.get_children():
            if linha.pagina == raiz:
                self.nav.select_row(linha)
        self._sincronizando = False
        self._desenhar_trilha()

    def _desenhar_trilha(self):
        for f in self.trilha.get_children():
            f.destroy()
        for i, (pagina, rotulo_, _f) in enumerate(self._trilha):
            atual = i == len(self._trilha) - 1
            b = Gtk.Button()
            caixa = Gtk.Box(spacing=6)
            if i == 0:
                caixa.pack_start(Gtk.Image.new_from_icon_name("go-home-symbolic", Gtk.IconSize.BUTTON),
                                 False, False, 0)
            texto = rotulo(rotulo_)
            texto.set_max_width_chars(28)
            caixa.pack_start(texto, False, False, 0)
            b.add(caixa)
            css(b, "ms-passo", *(["ms-passo-atual"] if atual else []))
            b.set_tooltip_text(rotulo_)
            if not atual:
                b.connect("clicked", lambda _b, n=i + 1: self._ir_trilha(n))
            self.trilha.pack_start(b, False, False, 0)
        self.trilha.show_all()
        self.btn_voltar.set_sensitive(len(self._trilha) > 1)

    def _ir_trilha(self, tamanho):
        self._trilha = self._trilha[:tamanho]
        self._mostrar()

    def ir_para(self, pagina):
        for linha in self.nav.get_children():
            if linha.pagina == pagina:
                self.nav.unselect_all()
                self.nav.select_row(linha)

    def _empilhar(self, pagina, rotulo_, restaurar):
        if self._trilha and self._trilha[-1][0] == pagina:
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
        self.contadores["galeria"].set_text(str(len(self.app.nuvem.galeria())))
        self.contadores["minhas"].set_text(str(len(self.app.skins.do_usuario())))
        self.btn_desfazer.set_sensitive(self.app.skins.pode_desfazer())
        self._rodape()
        for p in self.paginas.values():
            p.atualizar()

    def card_local(self, skin):
        ativa = self.ativa is not None and skin.id == self.ativa.id
        selos = [("Em uso", True)] if ativa else []
        if skin.extras.get("nuvem_id"):
            selos.append(("Na conta", False))
        quando = "Atualizada" if skin.foi_atualizada else "Salva"
        menu = [("Renomear…", lambda: self.renomear(skin))]
        if ativa:
            menu.append(("Atualizar com a tela", lambda: self.atualizar(skin)))
        menu += [("Trocar capa…", lambda: self.trocar_capa(skin)),
                 ("Enviar para a conta…", lambda: self.enviar(skin)),
                 None,
                 ("Duplicar…", lambda: self.duplicar(skin)),
                 ("Exportar…", lambda: self.exportar(skin)),
                 ("Abrir pasta", lambda: self.abrir_pasta(skin.pasta)),
                 None,
                 ("Excluir…", lambda: self.excluir(skin), True)]
        principal = ("Aplicada", None, "ms-secundario") if ativa else \
            ("Aplicar", lambda: self.aplicar(skin), "ms-primario")
        return Card(self.app.capas.capa(skin), skin.nome, skin.responsavel,
                    f"{quando} em {data_br(skin.atualizado_em or skin.criado_em)}", selos, principal,
                    menu=menu, destaque=ativa, dica=skin.descricao)

    def acao_item(self, item):
        if not item.instalada:
            return "Baixar", lambda: self.baixar(item), "ms-primario"
        if self.ativa and self.ativa.id == item.skin_local:
            return "Aplicada", None, "ms-secundario"
        return "Aplicar", lambda: self.aplicar(self.app.skins.obter(item.skin_local)), "ms-primario"

    def card_item(self, item, dono=False):
        em_uso = bool(self.ativa and item.instalada and self.ativa.id == item.skin_local)
        selos = []
        if item.oficial:
            selos.append(("Oficial", True))
        if em_uso:
            selos.append(("Em uso", True))
        elif item.instalada and not item.oficial:
            selos.append(("Instalada", False))
        if not item.publica:
            selos.append(("Privada", False))
        detalhe = "Padrão do MintSkins" if item.oficial else \
            f"{item.downloads} download{'' if item.downloads == 1 else 's'} · {data_br(item.publicada_em, hora=False)}"
        menu = None
        if dono:
            menu = [("Tornar privada" if item.publica else "Publicar na galeria",
                     lambda: self.tornar_publica(item, not item.publica)),
                    None, ("Remover da conta…", lambda: self.remover_da_conta(item), True)]
        return Card(self.app.capas.capa(item), item.nome, item.autor_nome, detalhe, selos,
                    self.acao_item(item), favorito=(item.favorito, lambda v: self.favoritar(item, v), item.favoritos),
                    menu=menu, destaque=em_uso, cadeado=item.oficial, dica=item.descricao,
                    ao_abrir=lambda: self.abrir_detalhe(item),
                    ao_autor=lambda: self.abrir_perfil(item.autor_id))

    def tarefa(self, titulo, funcao, ao_terminar=None, sucesso=None):
        """Roda funcao(progresso) numa thread, com o painel de progresso."""
        if self.ocupado:
            return
        self.ocupado = True
        self.pilha.set_sensitive(False)
        self.toast.set_reveal_child(False)
        self.txt_titulo.set_text(titulo)
        self.txt_passo.set_text("Começando…")
        self.barra.set_fraction(0)
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
            dialogos.erro(self, f"{titulo}: não deu certo", str(falha))

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

    def aplicar(self, skin):
        if self.app.skins.precisa_backup():
            self.salvar_atual(primeiro_backup=True, depois=lambda: self.aplicar(skin))
            return
        prefs = self.app.skins.preferencias()
        self.tarefa(f"Aplicando “{skin.nome}”", lambda prog: self.app.skins.aplicar(skin, prefs, prog),
                    ao_terminar=lambda r: self.avisar(
                        f"“{skin.nome}” aplicada." + "".join(f" {a[:1].upper()}{a[1:]}." for a in r.avisos),
                        "Desfazer", self.desfazer, segundos=10))

    def desfazer(self):
        prefs = self.app.skins.preferencias()
        self.tarefa("Voltando ao visual anterior", lambda prog: self.app.skins.desfazer(prefs, prog),
                    sucesso="Visual anterior restaurado.")

    def salvar_atual(self, primeiro_backup=False, depois=None):
        if primeiro_backup:
            r = dialogos.pedir_nome(self, "Salve seu visual primeiro", "Salvar", "Meu visual original",
                                    com_capa=True, explicacao="Antes da primeira troca, guarde o visual "
                                    "atual como uma skin sua. Assim você sempre pode voltar a ele.")
        else:
            r = dialogos.pedir_nome(self, T.SALVAR, "Salvar", com_capa=True)
        if not r:
            return
        nome, desc, foto = r
        self._com_foto(foto, lambda capa: self.tarefa(
            f"Salvando “{nome}”", lambda prog: self.app.skins.salvar_atual(nome, desc, capa, prog),
            ao_terminar=lambda _s: depois and GLib.idle_add(depois),
            sucesso=lambda s: f"“{s.nome}” salva em Minhas skins."))

    def atualizar(self, skin):
        if dialogos.confirmar(self, f"Atualizar “{skin.nome}”?",
                              "A skin passa a guardar o visual que está na tela agora.", "Atualizar"):
            self._com_foto(True, lambda capa: self.tarefa(
                f"Atualizando “{skin.nome}”",
                lambda prog: self.app.skins.atualizar_com_atual(skin, capa, prog),
                sucesso=f"“{skin.nome}” atualizada."))

    def renomear(self, skin):
        r = dialogos.pedir_nome(self, "Renomear", "Salvar", skin.nome, skin.descricao)
        if r:
            self._rapido("Renomear", lambda: self.app.skins.editar(skin, r[0], r[1]))

    def duplicar(self, skin):
        r = dialogos.pedir_nome(self, "Duplicar", "Duplicar", f"{skin.nome} (cópia)", skin.descricao)
        if r:
            self.tarefa("Duplicando", lambda _p: self.app.skins.duplicar(skin, r[0], r[1]),
                        sucesso=lambda s: f"“{s.nome}” criada em Minhas skins.")

    def excluir(self, skin):
        if dialogos.confirmar(self, f"Excluir “{skin.nome}”?",
                              "A skin sai deste computador. O visual da tela não muda.", "Excluir",
                              destrutivo=True):
            self._rapido("Excluir", lambda: self.app.skins.excluir(skin), f"“{skin.nome}” excluída.")

    def trocar_capa(self, skin):
        d = Gtk.FileChooserNative(title="Escolha a capa", transient_for=self,
                                  action=Gtk.FileChooserAction.OPEN, accept_label="Usar")
        f = Gtk.FileFilter()
        f.set_name("Imagens")
        f.add_pixbuf_formats()
        d.add_filter(f)
        if d.run() == Gtk.ResponseType.ACCEPT:
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(d.get_filename(), 1280, -1, True)
                tmp = Path(tempfile.mkstemp(suffix=".png")[1])
                pix.savev(str(tmp), "png", [], [])
                self._rapido("Trocar capa", lambda: self.app.skins.trocar_capa(skin, tmp))
                tmp.unlink(missing_ok=True)
            except GLib.Error as e:
                dialogos.erro(self, "Imagem inválida", str(e))
        d.destroy()

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

    def abrir_detalhe(self, item):
        self._empilhar("detalhe", item.nome, lambda: self.paginas["detalhe"].mostrar(item))

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

    def enviar(self, skin):
        if not self.conta:
            self.avisar("Entre na sua conta para enviar skins.", "Entrar", lambda: self.ir_para("conta"))
            return
        escolha = dialogos.escolher(self, f"Enviar “{skin.nome}”", [
            ("privada", "Só para mim", "Fica na sua conta, para baixar em outro computador."),
            ("publica", "Publicar na galeria", "Qualquer pessoa pode ver, baixar e favoritar."),
        ], "Enviar")
        if escolha:
            publica = escolha == "publica"
            self.tarefa("Enviando", lambda _p: self.app.nuvem.enviar(skin, publica),
                        sucesso="Publicada na galeria." if publica else "Guardada na sua conta.")

    def tornar_publica(self, item, publica):
        self._rapido("Alterar", lambda: self.app.nuvem.definir_publica(item, publica),
                     "Publicada na galeria." if publica else "Agora só você vê esta skin.")

    def remover_da_conta(self, item):
        if dialogos.confirmar(self, f"Remover “{item.nome}” da conta?",
                              "Ela sai da sua conta e da galeria. A cópia neste computador continua.",
                              "Remover", destrutivo=True):
            self._rapido("Remover", lambda: self.app.nuvem.remover(item), "Removida da conta.")

    def entrar(self, criar, dados, erro):
        try:
            if criar:
                self.app.nuvem.criar_conta(dados.get("nome", ""), dados["email"], dados["senha"])
            else:
                self.app.nuvem.entrar(dados["email"], dados["senha"])
        except MintSkinsErro as e:
            erro.set_text(str(e))
            erro.show()
            return
        self.recarregar()
        self.avisar(f"Olá, {self.conta.nome.split()[0]}!")

    def sair(self):
        self.app.nuvem.sair()
        self.recarregar()
        self.avisar("Você saiu da conta.")

    def verificar_versao(self, manual):
        def depois(nova):
            self.nova_versao = nova
            self.paginas["inicio"].atualizar()
            if nova:
                self.avisar(f"MintSkins {nova.versao} disponível.", "Atualizar", self.atualizar_app, segundos=12)
            elif manual:
                self.avisar(f"Você já tem a versão mais recente ({__version__}).")

        def rodar():
            nova = None
            try:
                nova = self.app.atualizacoes.verificar(forcar=manual)
            except MintSkinsErro as e:
                if manual:
                    GLib.idle_add(dialogos.erro, self, "Atualizações", str(e))
            GLib.idle_add(depois, nova)
        threading.Thread(target=rodar, daemon=True).start()

    def atualizar_app(self):
        nova = self.nova_versao
        if not nova:
            return
        if not nova.pacote_url:
            self.abrir_url(nova.pagina)
            return
        notas = (nova.notas or "Correções e melhorias.").strip()
        if dialogos.confirmar(self, f"Atualizar para o MintSkins {nova.versao}?",
                              f"{notas[:600]}\n\nO pacote vem do GitHub do projeto. "
                              "Pede a senha de administrador.", "Atualizar"):
            self.tarefa(f"Atualizando para {nova.versao}", lambda _p: self.app.atualizacoes.atualizar(nova),
                        ao_terminar=lambda _r: self.avisar("Atualizado. Reinicie para usar a versão nova.",
                                                           "Reiniciar", self.reiniciar, segundos=30))

    def ignorar_versao(self):
        if self.nova_versao:
            self.app.atualizacoes.ignorar(self.nova_versao)
        self.nova_versao = None
        self.paginas["inicio"].atualizar()

    def reiniciar(self):
        subprocess.Popen(["sh", "-c", "sleep 1; exec mintskins"], start_new_session=True)
        self.get_application().quit()

    def mudar_preferencia(self, campo, valor):
        prefs = self.app.skins.preferencias()
        setattr(prefs, campo, valor)
        self.app.skins.gravar_preferencias(prefs)

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
