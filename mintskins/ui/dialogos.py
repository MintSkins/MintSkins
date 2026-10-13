"""Dialogos modais."""
from gi.repository import Gtk

from .widgets import css, rotulo


def erro(pai, titulo, texto):
    d = Gtk.MessageDialog(transient_for=pai, modal=True, message_type=Gtk.MessageType.ERROR,
                          buttons=Gtk.ButtonsType.OK, text=titulo)
    d.format_secondary_text(texto)
    css(d, "ms-janela")
    d.run()
    d.destroy()


def confirmar(pai, titulo, texto, botao, destrutivo=False):
    d = Gtk.MessageDialog(transient_for=pai, modal=True, message_type=Gtk.MessageType.QUESTION,
                          text=titulo)
    d.format_secondary_text(texto)
    d.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    css(d.add_button(botao, Gtk.ResponseType.OK), "ms-perigo" if destrutivo else "ms-primario")
    css(d, "ms-janela")
    r = d.run()
    d.destroy()
    return r == Gtk.ResponseType.OK


def pedir_nome(pai, titulo, botao, nome="", descricao="", com_capa=False, explicacao=None):
    """Devolve (nome, descricao, usar_foto_da_tela) ou None se cancelou."""
    d = Gtk.Dialog(title=titulo, transient_for=pai, modal=True, use_header_bar=True)
    d.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    css(d, "ms-janela")
    ok = css(d.add_button(botao, Gtk.ResponseType.OK), "ms-primario")
    d.set_default_response(Gtk.ResponseType.OK)
    grade = Gtk.Grid(row_spacing=10, column_spacing=12, margin=20)
    linha = 0
    if explicacao:
        grade.attach(rotulo(explicacao, ["ms-dim"], wrap=True), 0, linha, 2, 1)
        linha += 1
    e_nome = Gtk.Entry(text=nome, activates_default=True, hexpand=True, width_chars=36,
                       placeholder_text="Ex.: Mint escuro com dock")
    e_desc = Gtk.Entry(text=descricao, activates_default=True,
                       placeholder_text="Opcional — algo para lembrar o que tem nela")
    grade.attach(rotulo("Nome", ["ms-dim"]), 0, linha, 1, 1)
    grade.attach(e_nome, 1, linha, 1, 1)
    grade.attach(rotulo("Descrição", ["ms-dim"]), 0, linha + 1, 1, 1)
    grade.attach(e_desc, 1, linha + 1, 1, 1)
    foto = None
    if com_capa:
        foto = Gtk.CheckButton(label="Usar uma foto da tela como capa", active=True)
        grade.attach(foto, 1, linha + 2, 1, 1)
    e_nome.connect("changed", lambda e: ok.set_sensitive(bool(e.get_text().strip())))
    ok.set_sensitive(bool(nome.strip()))
    d.get_content_area().add(grade)
    d.show_all()
    r = d.run()
    res = (e_nome.get_text().strip(), e_desc.get_text().strip(), foto.get_active() if foto else False)
    d.destroy()
    return res if r == Gtk.ResponseType.OK and res[0] else None


def escolher(pai, titulo, opcoes, botao):
    """opcoes = [(id, titulo, descricao)]. Devolve o id escolhido ou None."""
    d = Gtk.Dialog(title=titulo, transient_for=pai, modal=True, use_header_bar=True)
    css(d, "ms-janela")
    d.add_button("Cancelar", Gtk.ResponseType.CANCEL)
    css(d.add_button(botao, Gtk.ResponseType.OK), "ms-primario")
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=20)
    primeiro, botoes = None, {}
    for chave, tit, desc in opcoes:
        r = Gtk.RadioButton.new_from_widget(primeiro)
        primeiro = primeiro or r
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        textos.pack_start(rotulo(tit, ["ms-card-nome"]), False, False, 0)
        textos.pack_start(rotulo(desc, ["ms-dim", "ms-pequeno"], wrap=True), False, False, 0)
        r.add(textos)
        botoes[chave] = r
        caixa.pack_start(r, False, False, 0)
    d.get_content_area().add(caixa)
    d.show_all()
    ok = d.run() == Gtk.ResponseType.OK
    escolha = next((k for k, r in botoes.items() if r.get_active()), None)
    d.destroy()
    return escolha if ok else None
