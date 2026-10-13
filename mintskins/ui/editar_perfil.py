"""Modal "Editar perfil": foto, nome, e-mail, bio e senha."""
import tempfile
from pathlib import Path

from gi.repository import GdkPixbuf, GLib, Gtk

from ..dominio.conta import BIO_MAXIMA
from .modal import ModalBorrado
from .widgets import avatar, botao, css, rotulo

LADO_FOTO = 256


def foto_quadrada(caminho):
    """Recorta o centro da imagem num quadrado de 256 px e grava um PNG temporario."""
    pix = GdkPixbuf.Pixbuf.new_from_file(str(caminho))
    pix = pix.apply_embedded_orientation() or pix
    w, h = pix.get_width(), pix.get_height()
    lado = min(w, h)
    pix = pix.new_subpixbuf((w - lado) // 2, (h - lado) // 2, lado, lado)
    pix = pix.scale_simple(LADO_FOTO, LADO_FOTO, GdkPixbuf.InterpType.HYPER)
    destino = Path(tempfile.mkstemp(prefix="mintskins-foto-", suffix=".png")[1])
    pix.savev(str(destino), "png", [], [])
    return destino


class ModalPerfil(ModalBorrado):
    def __init__(self, alvo, ao_salvar, ao_fechar=None):
        """ao_salvar(dados) devolve None se deu certo ou o texto do erro."""
        super().__init__(alvo, ao_fechar, largura=500)
        self.ao_salvar = ao_salvar
        self.conteudo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.cartao.pack_start(self.conteudo, False, False, 0)

    def editar(self, variante, conta):
        for f in self.conteudo.get_children():
            f.destroy()
        self.conta = conta
        self.foto_nova, self.remover_foto = None, False
        c = self.conteudo
        c.pack_start(rotulo("Editar perfil", ["ms-popup-titulo"]), False, False, 0)

        linha_foto = Gtk.Box(spacing=16)
        self.caixa_avatar = Gtk.Box()
        linha_foto.pack_start(self.caixa_avatar, False, False, 0)
        botoes_foto = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        botoes_foto.pack_start(botao("Trocar foto…", "ms-secundario", ao_clicar=self._escolher_foto),
                               False, False, 0)
        self.btn_remover = botao("Remover", "ms-fantasma", ao_clicar=self._tirar_foto)
        botoes_foto.pack_start(self.btn_remover, False, False, 0)
        linha_foto.pack_start(botoes_foto, False, False, 0)
        c.pack_start(linha_foto, False, False, 0)

        self.nome = self._campo(c, "Nome", conta.nome, max_len=60)
        self.email = self._campo(c, "E-mail", conta.email)
        self.email.set_input_purpose(Gtk.InputPurpose.EMAIL)
        self.bio = self._campo(c, "Bio", conta.bio, max_len=BIO_MAXIMA,
                               dica="Uma frase sobre você, aparece no seu perfil público")
        self.contador = rotulo("", ["ms-dim", "ms-pequeno"], xalign=1.0)
        c.pack_start(self.contador, False, False, 0)
        self.bio.connect("changed", lambda e: self.contador.set_text(f"{len(e.get_text())}/{BIO_MAXIMA}"))
        self.bio.emit("changed")

        senha = Gtk.Expander(label="Alterar senha")
        css(senha, "ms-expansor")
        caixa_senha = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=10)
        self.senha_atual = self._campo(caixa_senha, "Senha atual", "", senha=True)
        self.senha_nova = self._campo(caixa_senha, "Nova senha", "", senha=True, dica="pelo menos 8 caracteres")
        self.senha_conf = self._campo(caixa_senha, "Repita a nova senha", "", senha=True)
        senha.add(caixa_senha)
        c.pack_start(senha, False, False, 0)

        self.erro = rotulo("", ["ms-erro", "ms-pequeno"], wrap=True)
        c.pack_start(self.erro, False, False, 0)
        botoes = Gtk.Box(spacing=8)
        self.btn_salvar = botao("Salvar", "ms-primario", ao_clicar=self._salvar)
        botoes.pack_end(self.btn_salvar, False, False, 0)
        botoes.pack_end(botao("Cancelar", "ms-secundario", ao_clicar=self.fechar), False, False, 0)
        c.pack_start(botoes, False, False, 0)

        self._mostrar_avatar()
        self.abrir(variante)
        self.cartao.show_all()
        self.erro.hide()
        self.btn_remover.set_visible(bool(conta.foto))
        self.nome.grab_focus()

    def _campo(self, caixa, titulo, valor, senha=False, max_len=0, dica=""):
        caixa.pack_start(rotulo(titulo, ["ms-dim", "ms-pequeno"]), False, False, 0)
        e = css(Gtk.Entry(text=valor or "", visibility=not senha, max_length=max_len), "ms-campo")
        if senha:
            e.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        if dica:
            e.set_placeholder_text(dica)
        e.connect("activate", lambda _e: self._salvar())
        caixa.pack_start(e, False, False, 0)
        return e

    def _mostrar_avatar(self):
        for f in self.caixa_avatar.get_children():
            f.destroy()
        foto = None if self.remover_foto else (self.foto_nova or self.conta.foto)
        fake = type("Quem", (), {"iniciais": self.conta.iniciais, "foto": str(foto) if foto else None})
        self.caixa_avatar.pack_start(avatar(fake, grande=True), False, False, 0)
        self.caixa_avatar.show_all()

    def _escolher_foto(self):
        d = Gtk.FileChooserNative(title="Escolha sua foto", transient_for=self.get_toplevel(),
                                  action=Gtk.FileChooserAction.OPEN, accept_label="Usar")
        f = Gtk.FileFilter()
        f.set_name("Imagens")
        f.add_pixbuf_formats()
        d.add_filter(f)
        if d.run() == Gtk.ResponseType.ACCEPT:
            try:
                self.foto_nova, self.remover_foto = foto_quadrada(d.get_filename()), False
                self.btn_remover.show()
                self._mostrar_avatar()
            except GLib.Error:
                self._mostrar_erro("Não foi possível abrir essa imagem.")
        d.destroy()

    def _tirar_foto(self):
        self.foto_nova, self.remover_foto = None, True
        self.btn_remover.hide()
        self._mostrar_avatar()

    def _mostrar_erro(self, texto):
        self.erro.set_text(texto)
        self.erro.show()

    def _salvar(self):
        dados = {"nome": self.nome.get_text(), "email": self.email.get_text(), "bio": self.bio.get_text(),
                 "foto_nova": self.foto_nova, "remover_foto": self.remover_foto,
                 "senha_atual": self.senha_atual.get_text(), "senha_nova": self.senha_nova.get_text()}
        if dados["senha_nova"] or dados["senha_atual"]:
            if dados["senha_nova"] != self.senha_conf.get_text():
                self._mostrar_erro("A nova senha e a repetição não são iguais.")
                return
        erro = self.ao_salvar(dados)
        if erro:
            self._mostrar_erro(erro)
        else:
            self.fechar()
