"""Páginas da janela. Cada uma monta seus widgets e sabe se atualizar.

O layout segue o mintskins.com: sobrelinha amarela, titulo grande condensado, trilhos e grades de cards.
"""
from datetime import datetime

from gi.repository import Gtk

from .. import __version__
from ..aplicacao.servico_nuvem import LOCAL
from ..dominio.erros import MintSkinsErro
from . import textos as T
from .vitrine import Vitrine
from .widgets import (Avatar, avatar, Capa, botao, css, data_br, display, grade, icone,
                      numeros, opcao, preencher, rotulo, rotulo_tecnico, sobrelinha, tamanho_br, trilho, vazio)


def contar(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def rolavel(conteudo):
    rol = css(Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER), "ms-pagina")
    rol.add(conteudo)
    return rol


def cabecalho(sobre, titulo, subtitulo=None, *extras):
    """Como o topo das paginas do site: sobrelinha, titulo grande e uma frase."""
    cab = Gtk.Box(spacing=16)
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, valign=Gtk.Align.END)
    if sobre:
        textos.pack_start(sobrelinha(sobre), False, False, 0)
    textos.pack_start(display(titulo, "l"), False, False, 0)
    if subtitulo:
        textos.pack_start(rotulo(subtitulo, ["ms-dim"], wrap=True), False, False, 0)
    cab.pack_start(textos, True, True, 0)
    for e in reversed(extras):
        e.set_valign(Gtk.Align.END)
        cab.pack_end(e, False, False, 0)
    return cab


def titulo_secao(sobre, titulo, *extras):
    cab = Gtk.Box(spacing=12)
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, valign=Gtk.Align.END)
    if sobre:
        textos.pack_start(sobrelinha(sobre), False, False, 0)
    textos.pack_start(display(titulo, "s", wrap=False), False, False, 0)
    cab.pack_start(textos, True, True, 0)
    for e in reversed(extras):
        if e is not None:
            e.set_valign(Gtk.Align.END)
            cab.pack_end(e, False, False, 0)
    return cab


def painel(titulo, *filhos, espaco=12):
    caixa = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=espaco), "ms-painel")
    if titulo:
        caixa.pack_start(rotulo(titulo.upper(), ["ms-titulo-cartao"]), False, False, 4)
    for f in filhos:
        caixa.pack_start(f, False, False, 0)
    return caixa


def grupo(titulo, linhas):
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    if titulo:
        caixa.pack_start(rotulo(titulo.upper(), ["ms-titulo-cartao"]), False, False, 0)
    cartao = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "ms-grupo")
    for i, l in enumerate(linhas):
        if i:
            cartao.pack_start(Gtk.Separator(), False, False, 0)
        cartao.pack_start(l, False, False, 0)
    caixa.pack_start(cartao, False, False, 0)
    return caixa


def linha(titulo, descricao=None, controle=None):
    caixa = css(Gtk.Box(spacing=16), "ms-grupo-linha")
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER)
    textos.pack_start(rotulo(titulo, ["ms-card-nome"]), False, False, 0)
    if descricao:
        textos.pack_start(rotulo(descricao, ["ms-dim", "ms-pequeno"], wrap=True), False, False, 0)
    caixa.pack_start(textos, True, True, 0)
    if controle:
        controle.set_valign(Gtk.Align.CENTER)
        caixa.pack_end(controle, False, False, 0)
    return caixa


def valor(texto, destaque=False):
    return rotulo(texto, ["ms-autor-mintskins"] if destaque else ["ms-dim"])


def ficha(pares):
    """Lista "nome ........ valor" dentro de um painel."""
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    for nome, v in pares:
        l = Gtk.Box(spacing=12)
        l.pack_start(rotulo(nome.upper(), ["ms-rotulo-tecnico"], cortar=False), False, False, 0)
        l.pack_end(rotulo(v or "—", ["ms-sobre-texto"]), False, False, 0)
        caixa.pack_start(l, False, False, 0)
    return caixa


def aviso(icone_nome, titulo, texto, acao=None, extra=None):
    caixa = css(Gtk.Box(spacing=16), "ms-aviso")
    caixa.pack_start(css(icone(icone_nome, Gtk.IconSize.DND), "ms-aviso-icone"), False, False, 0)
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
    caixa.titulo = rotulo(titulo, ["ms-card-nome"], wrap=True)
    textos.pack_start(caixa.titulo, False, False, 0)
    if texto:
        textos.pack_start(rotulo(texto, ["ms-dim"], wrap=True), False, False, 0)
    caixa.pack_start(textos, True, True, 0)
    for b in (extra, acao):
        if b:
            botao_ = botao(b[0], b[2] if len(b) > 2 else "ms-primario", ao_clicar=b[1])
            botao_.set_valign(Gtk.Align.CENTER)
            caixa.pack_end(botao_, False, False, 0)
    return caixa


def busca(ao_mudar, exemplo="Buscar skins ou criadores"):
    e = css(Gtk.SearchEntry(placeholder_text=exemplo, width_chars=26), "ms-busca")
    e.connect("search-changed", lambda _e: ao_mudar())
    return e


def chips(opcoes, ao_mudar):
    """Filtros em botoes, so um marcado (como os filtros do site)."""
    caixa = Gtk.Box(spacing=8)
    primeiro = None
    for chave, texto in opcoes:
        b = css(Gtk.RadioButton.new_with_label_from_widget(primeiro, texto.upper()), "ms-chip")
        b.set_mode(False)
        primeiro = primeiro or b
        b.connect("toggled", lambda b, c=chave: b.get_active() and ao_mudar(c))
        caixa.pack_start(b, False, False, 0)
    return caixa


def capa_grande(capas, objeto):
    """Capa 16:9 que cresce com a janela."""
    quadro = Gtk.AspectFrame(ratio=16 / 9, obey_child=False, shadow_type=Gtk.ShadowType.NONE,
                             xalign=0, yalign=0)
    c = Capa(520, 293, raio=8)
    c.definir(capas.capa(objeto))
    quadro.add(c)
    return quadro


def coluna_lateral(largura=400):
    col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
    col.set_size_request(largura, -1)
    return col


class Pagina:
    def __init__(self, janela):
        self.j = janela
        self.caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=36, margin=40, margin_top=32)
        self.widget = rolavel(self.caixa)

    def limpar(self):
        for f in self.caixa.get_children():
            f.destroy()

    def visivel(self):
        return self.j.pilha.get_visible_child() is self.widget

    def atualizar(self):
        pass


class Inicio(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.vitrine = Vitrine(j)
        self.aviso_backup = aviso("dialog-warning-symbolic", T.AVISO_BACKUP_TITULO, T.AVISO_BACKUP_TEXTO,
                                  (T.SALVAR, lambda: j.salvar_atual(primeiro_backup=True)))
        self.em_uso = Gtk.Box()
        self.minhas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.galeria = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        for w in (self.vitrine, self.aviso_backup, self.em_uso, self.minhas, self.galeria):
            self.caixa.pack_start(w, False, False, 0)

    def atualizar(self):
        j = self.j
        galeria = j.app.nuvem.galeria()
        self.vitrine.definir(galeria)
        self.vitrine.set_visible(bool(galeria))
        self.aviso_backup.set_visible(j.app.skins.precisa_backup())
        self._em_uso(j.ativa)
        minhas = j.app.skins.do_usuario()
        self._trilho(self.minhas, "Neste computador", "Suas skins", [j.card_local(s, minhas) for s in minhas[:12]],
                     ("Ver todas", lambda: j.ir_para("minhas")), vazio(*T.VAZIO_MINHAS, (T.SALVAR, j.salvar_atual)))
        self._trilho(self.galeria, "Comunidade", "Em alta na galeria", [j.card_item(i, lista=galeria) for i in galeria[:12]],
                     ("Abrir galeria", lambda: j.ir_para("galeria")))

    def _trilho(self, caixa, sobre, titulo, cards, ver_mais, vazio_=None):
        for f in caixa.get_children():
            f.destroy()
        if not cards and not vazio_:
            caixa.hide()
            return
        rol, setas = trilho(cards)
        mais = botao(ver_mais[0], "ms-contorno", icone_nome="go-next-symbolic", icone_depois=True,
                     ao_clicar=ver_mais[1])
        caixa.pack_start(titulo_secao(sobre, titulo, mais, setas), False, False, 0)
        caixa.pack_start(rol if cards else vazio_, False, False, 0)
        caixa.show_all()
        setas.set_visible(len(cards) > 3)

    def _em_uso(self, ativa):
        j = self.j
        for f in self.em_uso.get_children():
            f.destroy()
        card = css(Gtk.Box(spacing=24), "ms-painel")
        capa = Capa(256, 144, raio=6)
        texto = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, valign=Gtk.Align.CENTER)
        botoes = Gtk.Box(spacing=8, margin_top=6)
        if ativa:
            capa.definir(j.app.capas.capa(ativa))
            texto.pack_start(rotulo_tecnico(T.EM_USO, "oficial" if ativa.incluida else f"v{ativa.versao}",
                                            "" if ativa.incluida else
                                            f"salva em {data_br(ativa.atualizado_em or ativa.criado_em, hora=False)}"),
                             False, False, 0)
            texto.pack_start(display(ativa.nome, "m"), False, False, 0)
            gtk_tema, icones = j.app.capas.temas(ativa)
            partes = [f"por {ativa.responsavel}", f"{gtk_tema} · {icones}" if gtk_tema else "",
                      "com dock" if ativa.dock else "sem dock"]
            texto.pack_start(rotulo(" · ".join(p for p in partes if p), ["ms-dim"], wrap=True), False, False, 0)
            if ativa.incluida:
                botoes.pack_start(botao("Duplicar para editar", "ms-contorno",
                                        ao_clicar=lambda: j.duplicar(ativa)), False, False, 0)
            else:
                botoes.pack_start(botao("Gerenciar", "ms-primario", icone_nome="go-next-symbolic", icone_depois=True,
                                        ao_clicar=lambda: j.abrir_skin(ativa)), False, False, 0)
                botoes.pack_start(botao(f"Atualizar (v{ativa.versao + 1})", "ms-contorno",
                                        icone_nome="view-refresh-symbolic",
                                        dica="Grava as mudanças que você fez no desktop como uma versão nova",
                                        ao_clicar=lambda: j.atualizar(ativa)), False, False, 0)
        else:
            capa.definir(j.app.capas.papel_de_parede_atual())
            texto.pack_start(rotulo_tecnico(T.EM_USO), False, False, 0)
            texto.pack_start(display(T.SEM_BACKUP_TITULO, "m"), False, False, 0)
            texto.pack_start(rotulo(T.SEM_BACKUP_TEXTO, ["ms-dim"], wrap=True), False, False, 0)
            botoes.pack_start(botao("Salvar como skin", "ms-primario", ao_clicar=j.salvar_atual), False, False, 0)
        texto.pack_start(botoes, False, False, 0)
        card.pack_start(capa, False, False, 0)
        card.pack_start(texto, True, True, 0)
        self.em_uso.pack_start(card, True, True, 0)
        self.em_uso.show_all()


class Galeria(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.filtro, self.ordem = "todas", "populares"
        self.busca = busca(self.atualizar)
        self.caixa.pack_start(cabecalho(*T.GALERIA), False, False, 0)
        barra = Gtk.Box(spacing=12)
        barra.pack_start(chips(T.FILTROS, self._filtrou), False, False, 0)
        barra.pack_end(self.busca, False, False, 0)
        ordem = Gtk.ComboBoxText()
        for chave, texto in T.ORDENS:
            ordem.append(chave, texto)
        ordem.set_active_id(self.ordem)
        ordem.connect("changed", lambda c: self._ordenou(c.get_active_id()))
        barra.pack_end(ordem, False, False, 0)
        lista = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.contagem = rotulo("", ["ms-rotulo-tecnico"])
        self.grade = grade()
        self.vazio = vazio(*T.VAZIO_GALERIA)
        for w in (self.contagem, self.grade, self.vazio):
            lista.pack_start(w, False, False, 0)
        self.caixa.pack_start(barra, False, False, 0)
        self.caixa.pack_start(lista, False, False, 0)

    def _filtrou(self, chave):
        self.filtro = chave
        self.atualizar()

    def _ordenou(self, chave):
        self.ordem = chave or "populares"
        self.atualizar()

    def atualizar(self):
        itens = self.j.app.nuvem.galeria(self.filtro, self.busca.get_text(), self.ordem)
        self.contagem.set_text(contar(len(itens), "skin encontrada", "skins encontradas").upper())
        preencher(self.grade, self.vazio, [self.j.card_item(i, lista=itens) for i in itens])
        textos = T.VAZIO_FAVORITAS if self.filtro == "favoritas" else T.VAZIO_GALERIA
        self.vazio.get_children()[0].set_text(textos[0].upper())
        self.vazio.get_children()[1].set_text(textos[1])


class Minhas(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.filtro = "todas"
        self.busca = busca(self.atualizar, "Buscar nas suas skins")
        self.caixa.pack_start(cabecalho(*T.MINHAS), False, False, 0)
        barra = Gtk.Box(spacing=12)
        barra.pack_start(chips(T.FILTROS_MINHAS, self._filtrou), False, False, 0)
        barra.pack_end(self.busca, False, False, 0)
        lista = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.contagem = rotulo("", ["ms-rotulo-tecnico"])
        self.grade = grade()
        self.vazio = vazio(*T.VAZIO_MINHAS, (T.SALVAR, j.salvar_atual))
        self.vazio_filtro = vazio("", "")     # filtro ou busca sem resultado: sem o botao de salvar
        for w in (self.contagem, self.grade, self.vazio, self.vazio_filtro):
            lista.pack_start(w, False, False, 0)
        self.caixa.pack_start(barra, False, False, 0)
        self.caixa.pack_start(lista, False, False, 0)

    def _filtrou(self, chave):
        self.filtro = chave
        self.atualizar()

    def atualizar(self):
        j, texto = self.j, self.busca.get_text()
        filtrando = self.filtro != "todas" or bool(texto.strip())
        titulo, frase = T.VAZIO_FILTRO_MINHAS.get(self.filtro if not texto.strip() else "busca",
                                                  T.VAZIO_FILTRO_MINHAS["busca"])
        self.vazio_filtro.get_children()[0].set_text(titulo.upper())
        self.vazio_filtro.get_children()[1].set_text(frase)
        todas = j.app.skins.do_usuario()
        skins = j.app.skins.do_usuario(texto)
        if self.filtro != "todas":
            skins = [s for s in skins if j.situacao(s)[0] == self.filtro]
        ligadas = {s.extras.get(k) for s in todas for k in ("nuvem_id", "galeria_id")}
        fora = [i for i in j.na_conta.values() if i.id not in ligadas and i.combina(texto)
                and self.filtro in ("todas", "publica" if i.publica else "privada")]
        resumo = contar(len(skins), "skin neste computador", "skins neste computador")
        if fora:
            resumo += " · " + contar(len(fora), "só na conta", "só na conta")
        self.contagem.set_text(resumo.upper())
        # uma grade so: primeiro as deste computador, depois as que estao so na conta (com Baixar)
        cards = [j.card_local(s, skins) for s in skins] + \
            [j.card_item(i, dono=True, lista=fora, so_na_conta=True) for i in fora]
        preencher(self.grade, self.vazio_filtro if filtrando else self.vazio, cards)
        (self.vazio if filtrando else self.vazio_filtro).set_visible(False)


class Detalhe(Pagina):
    """Skin da galeria, como a pagina da skin no site."""
    chave = None

    def mostrar(self, item):
        j = self.j
        self.item, self.chave = item, f"item:{item.id}"
        self.limpar()
        topo = Gtk.Box(spacing=36)
        topo.pack_start(capa_grande(j.app.capas, item), True, True, 0)
        lado = coluna_lateral()
        versao = item.extras.get("versao")
        quando = item.extras.get("atualizada_em") or item.publicada_em
        lado.pack_start(rotulo_tecnico("Oficial" if item.oficial else "Skin", f"v{versao}" if versao else "",
                                       f"atualizada {data_br(quando, hora=False)}" if quando else ""),
                        False, False, 0)
        lado.pack_start(display(item.nome, "l"), False, False, 0)

        autor = Gtk.Box(spacing=12)
        autor.pack_start(Avatar("".join(p[0] for p in item.autor_nome.split()[:2]).upper() or "?"), False, False, 0)
        nomes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0, valign=Gtk.Align.CENTER)
        nomes.pack_start(rotulo(item.autor_nome, ["ms-card-nome"]), False, False, 0)
        nomes.pack_start(rotulo(f"@{item.autor_id}", ["ms-apagado", "ms-pequeno"]), False, False, 0)
        autor.pack_start(nomes, True, True, 0)
        autor.pack_end(botao("Ver perfil", "ms-contorno", ao_clicar=lambda: j.abrir_perfil(item.autor_id)),
                       False, False, 0)
        lado.pack_start(autor, False, False, 0)

        if item.oficial:
            lado.pack_start(numeros([("Favoritos", item.favoritos), ("Dock", "Sim" if item.dock else "Não")]),
                            False, False, 0)
        else:
            lado.pack_start(numeros([("Downloads", item.downloads), ("Favoritos", item.favoritos),
                                     ("Versão", f"v{versao or 1}")]), False, False, 0)

        texto, cb, estilo = j.acao_item(item)
        if texto == "Baixar" and item.tamanho:
            texto = f"Baixar skin · {tamanho_br(item.tamanho)}"
        principal = botao(texto, estilo, "ms-grande", ao_clicar=cb,
                          icone_nome="folder-download-symbolic" if cb and estilo == "ms-primario" and "Baixar" in texto
                          else None)
        principal.set_sensitive(cb is not None)
        lado.pack_start(principal, False, False, 0)

        extras = Gtk.Box(spacing=8)
        fav = botao(f"{'Favoritada' if item.favorito else 'Favoritar'} · {item.favoritos}", "ms-contorno",
                    *(["ms-favorito-ativo"] if item.favorito else []),
                    icone_nome="starred-symbolic" if item.favorito else "non-starred-symbolic",
                    ao_clicar=lambda: j.favoritar(item, not item.favorito))
        extras.pack_start(fav, False, False, 0)
        pagina = item.extras.get("pagina")
        if pagina:
            extras.pack_start(botao("Copiar link", "ms-contorno", icone_nome="edit-copy-symbolic",
                                    ao_clicar=lambda: j.copiar_link(pagina)), False, False, 0)
            extras.pack_start(botao("Abrir no site", "ms-contorno", icone_nome="web-browser-symbolic",
                                    ao_clicar=lambda: j.abrir_url(pagina)), False, False, 0)
        lado.pack_start(extras, False, False, 0)

        tags = item.extras.get("tags") or []
        if tags:
            fila = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=6, row_spacing=6,
                               max_children_per_line=8)
            for t in tags:
                fila.add(css(Gtk.Label(label=f"#{t}".upper()), "ms-etiqueta"))
            lado.pack_start(fila, False, False, 0)

        local = self._skin_local_da_conta(item)
        if local:
            lado.pack_start(aviso("avatar-default-symbolic", "Esta skin é sua",
                                  "Publique, deixe privada ou envie uma atualização.",
                                  ("Gerenciar", lambda: j.abrir_skin(local))), False, False, 0)
        elif item.id in j.na_conta:
            dono = Gtk.Box(spacing=8)
            dono.pack_start(botao("Gerenciar na conta", "ms-contorno",
                                  ao_clicar=lambda: j.gerenciar_na_conta(item=item)), False, False, 0)
            lado.pack_start(dono, False, False, 0)
        topo.pack_start(lado, False, False, 0)
        self.caixa.pack_start(topo, False, False, 0)

        gtk_tema, icones = j.app.capas.temas(item)
        sobre = rotulo(item.descricao or "O autor não escreveu uma descrição.", ["ms-sobre-texto"], wrap=True)
        # tema e icones so se sabe das skins que ja estao neste computador
        pares = [("Tema", gtk_tema), ("Ícones", icones)] if gtk_tema else []
        if item.instalada or item.oficial:
            pares.append(("Dock", "Sim" if item.dock else "Não"))
        if not item.oficial:
            pares += [("Tamanho", tamanho_br(item.tamanho)), ("Publicada", data_br(item.publicada_em, hora=False))]
        detalhes = ficha(pares)
        como = rotulo("1.  " + ("Clique em Aplicar." if item.instalada else "Clique em Baixar: ela vai para "
                                "Minhas skins.") + "\n2.  Clique em Aplicar. O desktop muda na hora."
                      "\n3.  Para voltar ao visual anterior, use Desfazer (↶ no topo).",
                      ["ms-sobre-texto"], wrap=True)
        baixo = Gtk.Box(spacing=20, homogeneous=True)
        baixo.pack_start(painel("Sobre esta skin", sobre, Gtk.Separator(), detalhes), True, True, 0)
        baixo.pack_start(painel("Como aplicar", como), True, True, 0)
        self.caixa.pack_start(baixo, False, False, 0)

        outras = [(k, i) for k, i in self._outras(item)]
        if outras:
            rol, setas = trilho([j.card_item(i) for _k, i in outras])
            caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            caixa.pack_start(titulo_secao("Continue vendo", "Mais skins", setas), False, False, 0)
            caixa.pack_start(rol, False, False, 0)
            self.caixa.pack_start(caixa, False, False, 0)
            self.caixa.show_all()
            setas.set_visible(len(outras) > 3)
        self.caixa.show_all()

    def _outras(self, item):
        """As outras skins da lista de onde a pessoa veio (ou da galeria)."""
        ids = [k for k, _f in self.j._lista if k.startswith("item:")]
        itens = {f"item:{i.id}": i for i in self.j.app.nuvem.galeria()}
        if not ids:
            ids = list(itens)
        return [(k, itens[k]) for k in ids if k in itens and k != self.chave][:12]

    def _skin_local_da_conta(self, item):
        if item.id not in self.j.na_conta:
            return None
        return next((s for s in self.j.app.skins.do_usuario() if s.extras.get("nuvem_id") == item.id), None)

    def atualizar(self):
        if getattr(self, "item", None) and self.visivel():
            try:
                self.mostrar(self.j.app.nuvem.item(self.item.id))
            except MintSkinsErro:  # item removido enquanto estava aberto
                self.j.voltar()


class SkinLocal(Pagina):
    """Uma skin deste computador: aplicar, editar, publicar ou deixar privada, enviar atualizacao."""
    chave = None

    def mostrar(self, skin):
        j = self.j
        self.skin, self.chave = skin, f"skin:{skin.id}"
        self.limpar()
        ativa = bool(j.ativa and j.ativa.id == skin.id)
        onde, item = j.situacao(skin)

        topo = Gtk.Box(spacing=36)
        esquerda = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        esquerda.pack_start(capa_grande(j.app.capas, skin), True, True, 0)
        if skin.editavel:
            acoes_capa = Gtk.Box(spacing=8)
            acoes_capa.pack_start(botao("Trocar capa", "ms-contorno", icone_nome="image-x-generic-symbolic",
                                        ao_clicar=lambda: j.trocar_capa(skin)), False, False, 0)
            esquerda.pack_start(acoes_capa, False, False, 0)
        topo.pack_start(esquerda, True, True, 0)

        lado = coluna_lateral()
        origem = "Baixada da galeria" if skin.extras.get("galeria_id") and not skin.extras.get("nuvem_id") \
            else "Sua skin"
        lado.pack_start(rotulo_tecnico(origem, f"v{skin.versao}", f"salva {data_br(skin.criado_em, hora=False)}",
                                       f"atualizada {data_br(skin.atualizado_em, hora=False)}"
                                       if skin.foi_atualizada else ""), False, False, 0)
        lado.pack_start(display(skin.nome, "l"), False, False, 0)
        lado.pack_start(rotulo(skin.descricao or "Sem descrição.", ["ms-dim"], wrap=True), False, False, 0)
        editar = botao("Editar nome e descrição", "ms-fantasma", icone_nome="document-edit-symbolic",
                       ao_clicar=lambda: j.renomear(skin))
        editar.set_halign(Gtk.Align.START)
        lado.pack_start(editar, False, False, 0)
        if ativa:
            # em uso: o que se quer e guardar o que mudou no desktop, como uma versao nova
            lado.pack_start(botao(f"Salvar alterações · v{skin.versao + 1}", "ms-primario", "ms-grande",
                                  icone_nome="document-save-symbolic",
                                  dica="Grava nesta skin o que você mudou no desktop (tema, painel, papel de parede…)",
                                  ao_clicar=lambda: j.atualizar(skin)), False, False, 0)
            lado.pack_start(rotulo("Em uso agora. Mudou algo no desktop? Salve como uma versão nova.",
                                   ["ms-apagado", "ms-pequeno"], wrap=True), False, False, 0)
        else:
            lado.pack_start(botao("Aplicar", "ms-primario", "ms-grande", ao_clicar=lambda: j.aplicar(skin)),
                            False, False, 0)
        gtk_tema, icones = j.app.capas.temas(skin)
        lado.pack_start(ficha([("Tema", gtk_tema), ("Ícones", icones), ("Dock", "Sim" if skin.dock else "Não")]),
                        False, False, 4)
        topo.pack_start(lado, False, False, 0)
        self.caixa.pack_start(topo, False, False, 0)

        self.caixa.pack_start(self._onde(skin, onde, item), False, False, 0)
        self.caixa.pack_start(self._mais(skin), False, False, 0)
        self.caixa.show_all()

    def _onde(self, skin, onde, item):
        """Os tres lugares onde a skin pode ficar, lado a lado; o atual fica marcado."""
        j = self.j
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        caixa.pack_start(titulo_secao("Visibilidade", "Onde esta skin fica"), False, False, 0)
        if not j.conta:
            caixa.pack_start(aviso("avatar-default-symbolic", "Entre na sua conta para publicar",
                                   "Com a conta do mintskins.com você guarda suas skins e publica na galeria.",
                                   ("Entrar", lambda: j.ir_para("conta"))), False, False, 0)
        opcoes = Gtk.Box(spacing=12, homogeneous=True)
        for chave, icone_nome, titulo, texto in T.ONDE:
            if j.conta and chave != LOCAL:      # limite da conta: x/5 publicadas, x/5 guardadas
                texto += f" {'Publicadas' if chave == 'publica' else 'Guardadas'}: {j.uso(chave)}."
            b = opcao(icone_nome, titulo, texto, escolhida=chave == onde,
                      ao_clicar=lambda c=chave: j.mudar_situacao(skin, c))
            b.set_sensitive(chave == onde or chave == LOCAL and bool(j.conta) or
                            bool(j.conta) and chave != LOCAL and not j.cheio(chave))
            opcoes.pack_start(b, True, True, 0)
        caixa.pack_start(opcoes, False, False, 0)

        if onde != LOCAL and item:
            versao = item.extras.get("versao")
            enviada = skin.extras.get("enviada_em")
            info = [f"Na conta: v{versao}" if versao else "Na conta"]
            if enviada:
                info.append(f"enviada {data_br(datetime.fromisoformat(enviada), hora=False)}")
            if j.app.nuvem.pendente(skin):
                sinc = aviso("software-update-available-symbolic", "Você mudou esta skin depois do último envio",
                             " · ".join(info) + ". Envie para o site e para os outros computadores ficarem iguais.",
                             ("Enviar atualização", lambda: j.enviar_atualizacao(skin)))
            else:
                sinc = css(Gtk.Box(spacing=12), "ms-painel")
                sinc.pack_start(css(icone("object-select-symbolic", Gtk.IconSize.BUTTON), "ms-ok"), False, False, 0)
                sinc.pack_start(rotulo("Igual à versão da conta · " + " · ".join(info), ["ms-dim"]), True, True, 0)
                sinc.pack_end(botao("Enviar de novo", "ms-fantasma", dica="Manda a versão deste computador outra vez",
                                    ao_clicar=lambda: j.enviar_atualizacao(skin)), False, False, 0)
                if item.publica:
                    sinc.pack_end(botao("Ver na galeria", "ms-contorno",
                                        ao_clicar=lambda: j.abrir_detalhe(item)), False, False, 0)
                if item.extras.get("pagina"):
                    sinc.pack_end(botao("Abrir no site", "ms-contorno", icone_nome="web-browser-symbolic",
                                        ao_clicar=lambda: j.abrir_url(item.extras["pagina"])), False, False, 0)
            caixa.pack_start(sinc, False, False, 0)
        return caixa

    def _mais(self, skin):
        j = self.j
        linhas = [linha("Duplicar", "Cria uma cópia para mexer sem perder esta.",
                        botao("Duplicar", "ms-contorno", ao_clicar=lambda: j.duplicar(skin))),
                  linha("Exportar", "Gera um arquivo .mintskins para levar a outro computador.",
                        botao("Exportar", "ms-contorno", ao_clicar=lambda: j.exportar(skin))),
                  linha("Pasta da skin", None,
                        botao("Abrir pasta", "ms-contorno", ao_clicar=lambda: j.abrir_pasta(skin.pasta)))]
        if skin.editavel:
            linhas.append(linha("Excluir deste computador", "O visual da tela não muda. A cópia na conta continua.",
                                botao("Excluir", "ms-perigo", ao_clicar=lambda: j.excluir(skin))))
        return grupo("Mais ações", linhas)

    def atualizar(self):
        skin = getattr(self, "skin", None)
        if not skin:
            return
        try:
            novo = self.j.app.skins.obter(skin.id)
        except MintSkinsErro:
            self.skin = None
            if self.visivel():
                self.j.voltar()
            return
        if self.visivel():
            self.mostrar(novo)
        else:
            self.skin = novo


MESES_LONGOS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
                "outubro", "novembro", "dezembro"]


def data_longa(d):
    return f"{d.day} de {MESES_LONGOS[d.month - 1]} de {d.year}" if d else ""


def cabecalho_perfil(j, quem, itens, proprio):
    """Topo do perfil como no site: banner, foto, nome, @usuario, bio, links e numeros."""
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
    topo = css(Gtk.Overlay(), "ms-vitrine")
    banner = Capa(1000, 240, raio=10, escurecer=True)
    capa_skin = next((j.app.capas.capa(i) for i in itens), None)
    banner.definir(getattr(quem, "banner", None) or capa_skin)
    topo.add(banner)
    sobre = Gtk.Box(spacing=22, halign=Gtk.Align.START, valign=Gtk.Align.END, margin=28)
    sobre.pack_start(avatar(quem, grande=True), False, False, 0)
    nomes = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.END)
    desde = getattr(quem, "desde", None) or getattr(quem, "criada_em", None)
    nomes.pack_start(rotulo_tecnico("Oficial" if getattr(quem, "oficial", False) else "", f"@{quem.id}",
                                    f"na comunidade desde {data_longa(desde)}" if desde else ""), False, False, 0)
    nomes.pack_start(display(quem.nome, "l"), False, False, 0)
    sobre.pack_start(nomes, False, False, 0)
    topo.add_overlay(sobre)
    caixa.pack_start(topo, False, False, 0)

    linha_ = Gtk.Box(spacing=24)
    dados = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    if quem.bio:
        dados.pack_start(rotulo(quem.bio, ["ms-sobre-texto"], wrap=True), False, False, 0)
    links = Gtk.Box(spacing=20)
    if getattr(quem, "localizacao", ""):
        lugar = Gtk.Box(spacing=6)
        lugar.pack_start(css(icone("mark-location-symbolic"), "ms-apagado"), False, False, 0)
        lugar.pack_start(rotulo(quem.localizacao, ["ms-dim"]), False, False, 0)
        links.pack_start(lugar, False, False, 0)
    if getattr(quem, "site", ""):
        endereco = quem.site.split("://", 1)[-1].removeprefix("www.").rstrip("/")
        links.pack_start(botao(endereco, "ms-fantasma", icone_nome="web-browser-symbolic",
                               ao_clicar=lambda: j.abrir_url(quem.site)), False, False, 0)
    if getattr(quem, "github", ""):
        links.pack_start(botao(f"github.com/{quem.github}", "ms-fantasma", icone_nome="system-users-symbolic",
                               ao_clicar=lambda: j.abrir_url(f"https://github.com/{quem.github}")), False, False, 0)
    if links.get_children():
        dados.pack_start(links, False, False, 0)
    nums = Gtk.Box(spacing=28)
    pares = [(len(itens), "skin" if len(itens) == 1 else "skins")]
    if not getattr(quem, "oficial", False):
        pares += [(getattr(quem, "seguidores", 0), "seguidores"), (getattr(quem, "seguindo", 0), "seguindo")]
    for n, nome in pares:
        par = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        par.pack_start(rotulo(str(n), ["ms-numero-valor"], cortar=False), False, False, 0)
        par.pack_start(rotulo(nome.upper(), ["ms-rotulo-tecnico"], cortar=False), False, False, 0)
        nums.pack_start(par, False, False, 0)
    dados.pack_start(nums, False, False, 0)
    linha_.pack_start(dados, True, True, 0)

    acoes = Gtk.Box(spacing=8, valign=Gtk.Align.END)
    if proprio:
        acoes.pack_start(botao("Editar perfil", "ms-primario", icone_nome="document-edit-symbolic",
                               ao_clicar=j.editar_perfil), False, False, 0)
    elif not getattr(quem, "oficial", False):
        acoes.pack_start(botao("Seguir no site", "ms-primario", icone_nome="list-add-symbolic",
                               dica="Seguir acontece no mintskins.com", ao_clicar=lambda: j.ver_perfil(quem)),
                         False, False, 0)
    if not getattr(quem, "oficial", False):
        acoes.pack_start(botao("Ver no site", "ms-contorno", icone_nome="web-browser-symbolic",
                               ao_clicar=lambda: j.ver_perfil(quem)), False, False, 0)
        acoes.pack_start(botao("", "ms-contorno", "ms-icone-quadrado", icone_nome="edit-copy-symbolic",
                               dica="Copiar o link do perfil",
                               ao_clicar=lambda: j.copiar_link(getattr(quem, "pagina", "") or
                                                               f"{j.app.nuvem.site}/u/{quem.id}")), False, False, 0)
    linha_.pack_end(acoes, False, False, 0)
    caixa.pack_start(linha_, False, False, 0)
    caixa.pack_start(Gtk.Separator(), False, False, 0)
    return caixa


def secao_grade(sobre, titulo, cards, textos_vazio):
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    caixa.pack_start(titulo_secao(sobre, titulo), False, False, 0)
    g, v = grade(), vazio(*textos_vazio)
    caixa.pack_start(g, False, False, 0)
    caixa.pack_start(v, False, False, 0)
    caixa.preencher = lambda: preencher(g, v, cards)
    return caixa


class Perfil(Pagina):
    chave = None

    def mostrar(self, perfil):
        j = self.j
        self.perfil = perfil
        self.limpar()
        proprio = bool(j.conta and j.conta.id == perfil.id)
        if proprio:
            _juntar(perfil, j.conta)
        self.caixa.pack_start(cabecalho_perfil(j, perfil, perfil.itens, proprio), False, False, 0)
        secoes = [secao_grade("Publicadas", "Skins", [j.card_item(i, lista=perfil.itens) for i in perfil.itens],
                              ("Nenhuma skin publicada", "Quando publicar, as skins aparecem aqui."))]
        if proprio:
            favs = j.app.nuvem.favoritas()
            if favs:
                secoes.append(secao_grade("Curtidas", "Favoritas", [j.card_item(i, lista=favs) for i in favs],
                                          T.VAZIO_FAVORITAS))
        for s in secoes:
            self.caixa.pack_start(s, False, False, 0)
        self.caixa.show_all()
        for s in secoes:
            s.preencher()

    def atualizar(self):
        if getattr(self, "perfil", None) and self.visivel():
            p = self.j.app.nuvem.perfil(self.perfil.id)
            self.mostrar(p) if p else self.j.voltar()


def _juntar(perfil, conta):
    """No proprio perfil, os dados da conta (mais completos) por cima dos do perfil publico."""
    for campo in ("banner", "localizacao", "site", "github", "seguidores", "seguindo", "pagina", "bio", "foto"):
        if not getattr(perfil, campo, None) and getattr(conta, campo, None):
            setattr(perfil, campo, getattr(conta, campo))
    return perfil


class Conta(Pagina):
    def atualizar(self):
        self.limpar()
        conta = self.j.conta
        secoes = self._logado(conta) if conta else self._entrar()
        self.caixa.pack_start(rotulo(T.NUVEM_LOCAL, ["ms-legal"], wrap=True), False, False, 0)
        self.caixa.show_all()
        for s in secoes:
            s.preencher()

    def _entrar(self):
        """Entrar com a conta do mintskins.com. Criar conta e recuperar a senha sao no site (codigo por e-mail)."""
        site = self.j.app.nuvem.site
        self.caixa.pack_start(cabecalho("Conta", "Entrar", "Use o mesmo e-mail (ou @usuario) e senha do "
                                        "mintskins.com."), False, False, 0)
        cartao = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14), "ms-painel")
        cartao.set_halign(Gtk.Align.START)
        cartao.set_size_request(460, -1)
        campos = {}
        for chave, rot, senha in (("email", "E-mail ou usuário", False), ("senha", "Senha", True)):
            caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            caixa.pack_start(rotulo(rot.upper(), ["ms-rotulo-campo"]), False, False, 0)
            e = css(Gtk.Entry(visibility=not senha, activates_default=False), "ms-campo")
            if senha:
                e.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            else:
                e.set_placeholder_text("voce@exemplo.com ou @usuario")
            campos[chave] = e
            caixa.pack_start(e, False, False, 0)
            cartao.pack_start(caixa, False, False, 0)
        erro = rotulo("", ["ms-erro", "ms-pequeno"], wrap=True)
        erro.set_no_show_all(True)
        cartao.pack_start(erro, False, False, 0)
        acao = botao("Entrar", "ms-primario", "ms-grande",
                     ao_clicar=lambda: self.j.entrar(False, {k: e.get_text() for k, e in campos.items()}, erro))
        for e in campos.values():
            e.connect("activate", lambda _e: acao.clicked())
        cartao.pack_start(acao, False, False, 0)
        esqueci = botao("Esqueci a senha", "ms-fantasma", ao_clicar=lambda: self.j.abrir_url(f"{site}/senha/new"))
        esqueci.set_halign(Gtk.Align.START)
        cartao.pack_start(esqueci, False, False, 0)
        cartao.pack_start(Gtk.Separator(), False, False, 0)
        cartao.pack_start(rotulo("Ainda não tem conta? Crie no site (com e-mail, Google ou GitHub) e depois "
                                 "entre aqui.", ["ms-dim", "ms-pequeno"], wrap=True), False, False, 0)
        criar = botao("Criar conta no mintskins.com", "ms-contorno", icone_nome="web-browser-symbolic",
                      ao_clicar=lambda: self.j.abrir_url(f"{site}/conta/nova"))
        criar.set_halign(Gtk.Align.START)
        cartao.pack_start(criar, False, False, 0)
        self.caixa.pack_start(cartao, False, False, 0)
        return []

    def _logado(self, conta):
        j = self.j
        self.caixa.pack_start(cabecalho("Sua conta", "Conta", "Seu perfil no app e no site, e onde ficam as "
                                        "skins que você guardou."), False, False, 0)
        topo = css(Gtk.Box(spacing=22), "ms-painel")
        topo.pack_start(avatar(conta, grande=True), False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        textos.pack_start(rotulo_tecnico("Perfil", f"@{conta.id}"), False, False, 0)
        textos.pack_start(display(conta.nome, "m"), False, False, 0)
        if conta.bio:
            textos.pack_start(rotulo(conta.bio, ["ms-sobre-texto"], wrap=True), False, False, 0)
        topo.pack_start(textos, True, True, 0)
        botoes = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        botoes.pack_start(botao("Ver perfil", "ms-contorno", ao_clicar=lambda: j.abrir_perfil(conta.id)),
                          False, False, 0)
        botoes.pack_start(botao("Editar perfil", "ms-primario", icone_nome="document-edit-symbolic",
                                ao_clicar=j.editar_perfil), False, False, 0)
        topo.pack_end(botoes, False, False, 0)
        self.caixa.pack_start(topo, False, False, 0)

        def no_site(texto="Alterar no site"):
            return botao(texto, "ms-contorno", icone_nome="web-browser-symbolic", ao_clicar=j.conta_no_site)
        self.caixa.pack_start(grupo("Conta no mintskins.com", [
            linha("E-mail", conta.email, no_site()),
            linha("Senha", "Para trocar, o site pede a senha atual.", no_site()),
            linha("Login com Google ou GitHub", "Conecte ou desconecte as contas usadas para entrar.",
                  no_site("Gerenciar no site")),
            linha("Sair deste computador", f"Conta criada em {data_br(conta.criada_em, hora=False)}.",
                  botao("Sair", "ms-contorno", ao_clicar=j.sair)),
            linha("Excluir a conta", "Apaga a conta e as skins publicadas. Feito no site, com confirmação "
                  "por e-mail.", botao("Excluir no site", "ms-perigo", ao_clicar=j.conta_no_site)),
        ]), False, False, 0)

        itens = list(j.na_conta.values())
        favs = j.app.nuvem.favoritas()
        secoes = [secao_grade("Guardadas e publicadas", "Na minha conta",
                              [j.card_item(i, dono=True, lista=itens) for i in itens], T.VAZIO_NUVEM),
                  secao_grade("Favoritas", "Skins que você curtiu",
                              [j.card_item(i, lista=favs) for i in favs], T.VAZIO_FAVORITAS)]
        for s in secoes:
            self.caixa.pack_start(s, False, False, 0)
        return secoes


class Preferencias(Pagina):
    def __init__(self, j):
        super().__init__(j)
        prefs = j.app.skins.preferencias()
        self.caixa.pack_start(cabecalho(*T.PREFERENCIAS), False, False, 0)
        linhas = []
        for campo, titulo, desc in T.PREF_APLICAR:
            linhas.append(linha(titulo, desc, self._chave(prefs, campo)))
        self.caixa.pack_start(grupo("Ao aplicar uma skin", linhas), False, False, 0)

        combo = Gtk.ComboBoxText()
        for chave, texto in T.APARENCIAS:
            combo.append(chave, texto)
        combo.set_active_id(prefs.aparencia)
        combo.connect("changed", lambda c: j.mudar_aparencia(c.get_active_id()))
        self.caixa.pack_start(grupo("Aparência", [linha(*T.PREF_TEMA, combo)]), False, False, 0)

        inicio = Gtk.Switch(active=prefs.iniciar_com_sistema)
        inicio.connect("notify::active", lambda s, _p: j.mudar_inicio_automatico(s.get_active()))
        linhas = [linha("Iniciar com o sistema",
                        "Abre o MintSkins ao ligar o computador, direto no ícone perto do relógio.", inicio)]
        if j.get_application().bandeja:
            sw = Gtk.Switch(active=prefs.segundo_plano)
            sw.connect("notify::active", lambda s, _p: j.mudar_segundo_plano(s.get_active()))
            linhas.append(linha(
                "Continuar rodando ao fechar a janela",
                "O MintSkins fica no ícone perto do relógio e avisa quando sair versão nova. "
                "Para sair de vez, clique com o botão direito no ícone e escolha Fechar.", sw))
        self.caixa.pack_start(grupo("Segundo plano", linhas), False, False, 0)

        self.caixa.pack_start(grupo("Atualizações", [
            linha("Procurar versões novas", "Verifica no GitHub ao abrir e a cada 12 horas.",
                  self._chave(prefs, "verificar_atualizacoes")),
            linha(f"Versão instalada: {__version__}", None,
                  botao("Verificar agora", "ms-contorno", ao_clicar=lambda: j.verificar_versao(True))),
        ]), False, False, 0)

        self.caixa.pack_start(grupo("Avançado", [
            linha("Pasta das minhas skins", None,
                  botao("Abrir", "ms-contorno", ao_clicar=lambda: j.abrir_pasta(j.app.skins.pasta_minhas_skins()))),
            linha("Tela de login original", "Desfaz o visual aplicado na tela de login.",
                  botao("Restaurar", "ms-contorno", ao_clicar=j.restaurar_login)),
        ]), False, False, 0)

    def _chave(self, prefs, campo):
        sw = Gtk.Switch(active=getattr(prefs, campo))
        sw.connect("notify::active", lambda s, _p: self.j.mudar_preferencia(campo, s.get_active()))
        return sw


class Sobre(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.caixa.set_halign(Gtk.Align.CENTER)
        self.caixa.set_size_request(660, -1)
        logo = j.logo(320)
        logo.set_margin_top(12)
        self.caixa.pack_start(logo, False, False, 0)
        slogan = display(T.SLOGAN, "m", ["ms-display-destaque"])
        slogan.set_xalign(0.5)
        slogan.set_justify(Gtk.Justification.CENTER)
        self.caixa.pack_start(slogan, False, False, 0)
        self.caixa.pack_start(painel("Sobre nós", rotulo(T.SOBRE_NOS, ["ms-sobre-texto"], wrap=True)), False, False, 0)
        self.caixa.pack_start(grupo(None, [
            linha("Proprietário", None, valor(T.PROPRIETARIO, destaque=True)),
            linha("Versão", None, valor(__version__)),
            linha("Plataforma", None, valor("Linux Mint · Cinnamon")),
            linha("Site", None, botao("mintskins.com", "ms-contorno", icone_nome="web-browser-symbolic",
                                      ao_clicar=lambda: j.abrir_url(j.app.nuvem.site))),
            linha("Código", None, botao("Abrir no GitHub", "ms-contorno", icone_nome="web-browser-symbolic",
                                        ao_clicar=lambda: j.abrir_url(T.URL_PROJETO))),
        ]), False, False, 0)
        self.caixa.pack_start(rotulo(T.LEGAL, ["ms-legal"], xalign=0.5, wrap=True), False, False, 0)

