"""Páginas da janela. Cada uma monta seus widgets e sabe se atualizar."""
from datetime import datetime
from types import SimpleNamespace

from gi.repository import Gtk

from .. import __version__
from . import textos as T
from .widgets import (Avatar, BotaoFavorito, Capa, botao, css, data_br, grade, icone, link,
                      preencher, rotulo, tamanho_br, vazio)


def contar(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def rolavel(conteudo):
    rol = css(Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER), "ms-pagina")
    rol.add(conteudo)
    return rol


def cabecalho(titulo, subtitulo=None, *extras):
    cab = Gtk.Box(spacing=16)
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
    textos.pack_start(rotulo(titulo, ["ms-titulo-pagina"]), False, False, 0)
    if subtitulo:
        textos.pack_start(rotulo(subtitulo, ["ms-dim"], wrap=True), False, False, 0)
    cab.pack_start(textos, True, True, 0)
    for e in reversed(extras):
        e.set_valign(Gtk.Align.CENTER)
        cab.pack_end(e, False, False, 0)
    return cab


def grupo(titulo, linhas):
    caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    if titulo:
        caixa.pack_start(rotulo(titulo, ["ms-titulo-secao"]), False, False, 0)
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


def aviso(icone_nome, titulo, texto, acao=None, extra=None):
    caixa = css(Gtk.Box(spacing=16), "ms-aviso")
    caixa.pack_start(css(icone(icone_nome, Gtk.IconSize.DIALOG), "ms-aviso-icone"), False, False, 0)
    textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
    caixa.titulo = rotulo(titulo, ["ms-card-nome"], wrap=True)
    textos.pack_start(caixa.titulo, False, False, 0)
    textos.pack_start(rotulo(texto, ["ms-dim"], wrap=True), False, False, 0)
    caixa.pack_start(textos, True, True, 0)
    for b in (extra, acao):
        if b:
            botao_ = botao(b[0], b[2] if len(b) > 2 else "ms-primario", ao_clicar=b[1])
            botao_.set_valign(Gtk.Align.CENTER)
            caixa.pack_end(botao_, False, False, 0)
    return caixa


def busca(ao_mudar):
    e = css(Gtk.SearchEntry(placeholder_text="Buscar", width_chars=22), "ms-busca")
    e.connect("search-changed", lambda _e: ao_mudar())
    return e


def capa_grande(capas, objeto, largura=560):
    c = Capa(largura, round(largura * 9 / 16), raio=16)
    c.definir(capas.capa(objeto))
    return c


class Pagina:
    def __init__(self, janela):
        self.j = janela
        self.caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=26, margin=36, margin_top=28)
        self.widget = rolavel(self.caixa)

    def limpar(self):
        for f in self.caixa.get_children():
            f.destroy()

    def atualizar(self):
        pass


class Inicio(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.saudacao = rotulo("", ["ms-titulo-pagina"])
        self.resumo = rotulo("", ["ms-dim"])
        topo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        topo.pack_start(self.saudacao, False, False, 0)
        topo.pack_start(self.resumo, False, False, 0)
        self.aviso_versao = aviso("software-update-available-symbolic", "", "Veja o que mudou e atualize.",
                                  ("Atualizar", j.atualizar_app), ("Agora não", j.ignorar_versao, "ms-secundario"))
        self.aviso_backup = aviso("dialog-warning-symbolic", T.AVISO_BACKUP_TITULO, T.AVISO_BACKUP_TEXTO,
                                  (T.SALVAR, lambda: j.salvar_atual(primeiro_backup=True)))
        self.hero = Gtk.Box()
        self.recentes = self._secao("Suas skins recentes", "Ver todas", "minhas")
        self.vazio_recentes = vazio(*T.VAZIO_MINHAS, (T.SALVAR, j.salvar_atual))
        self.destaques = self._secao("Destaques da galeria", "Abrir galeria", "galeria")
        for w in (topo, self.aviso_versao, self.aviso_backup, self.hero, self.recentes.caixa,
                  self.vazio_recentes, self.destaques.caixa):
            self.caixa.pack_start(w, False, False, 0)

    def _secao(self, titulo, ver_mais, destino):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        cab = Gtk.Box(spacing=12)
        cab.pack_start(rotulo(titulo, ["ms-titulo-secao"]), True, True, 0)
        mais = botao(ver_mais, "ms-fantasma", ao_clicar=lambda: self.j.ir_para(destino))
        mais.get_child().set_halign(Gtk.Align.END)
        cab.pack_end(mais, False, False, 0)
        caixa.pack_start(cab, False, False, 0)
        g = grade()
        caixa.pack_start(g, False, False, 0)
        return SimpleNamespace(caixa=caixa, grade=g)

    def atualizar(self):
        j = self.j
        hora = datetime.now().hour
        ola = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
        nome = (j.conta.nome if j.conta else j.app.skins.usuario).split()[0]
        self.saudacao.set_text(f"{ola}, {nome}")
        minhas = j.app.skins.do_usuario()
        galeria = j.app.nuvem.galeria()
        self.resumo.set_text(f"{contar(len(minhas), 'skin salva', 'skins salvas')} · {len(galeria)} na galeria")
        nova = j.nova_versao
        self.aviso_versao.set_visible(bool(nova))
        if nova:
            self.aviso_versao.titulo.set_text(f"MintSkins {nova.versao} disponível")
        self.aviso_backup.set_visible(j.app.skins.precisa_backup())
        self._hero(j.ativa)
        preencher(self.recentes.grade, self.vazio_recentes, [j.card_local(s) for s in minhas[:4]])
        self.recentes.caixa.set_visible(bool(minhas))
        destaques = [j.card_item(i) for i in galeria[:4]]
        for f in self.destaques.grade.get_children():
            f.destroy()
        for c in destaques:
            self.destaques.grade.add(c)
        self.destaques.grade.show_all()
        self.destaques.caixa.set_visible(bool(destaques))

    def _hero(self, ativa):
        j = self.j
        for f in self.hero.get_children():
            f.destroy()
        card = css(Gtk.Box(spacing=24), "ms-hero")
        capa = Capa(384, 216, raio=14)
        texto = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        texto.pack_start(rotulo(T.EM_USO, ["ms-sobrelinha"]), False, False, 0)
        botoes = Gtk.Box(spacing=8, margin_top=12)
        if ativa:
            capa.definir(j.app.capas.capa(ativa))
            texto.pack_start(rotulo(ativa.nome, ["ms-titulo-hero"]), False, False, 0)
            texto.pack_start(rotulo(f"por {ativa.responsavel}",
                                    ["ms-autor-mintskins" if ativa.incluida else "ms-dim"]), False, False, 0)
            if ativa.descricao:
                texto.pack_start(rotulo(ativa.descricao, ["ms-dim"], wrap=True), False, False, 0)
            gtk_tema, icones = j.app.capas.temas(ativa)
            partes = [T.OFICIAL_SOMENTE_LEITURA if ativa.incluida else f"Salva em {data_br(ativa.criado_em)}",
                      f"{gtk_tema} · {icones}" if gtk_tema else "", "Com dock" if ativa.dock else "Sem dock"]
            texto.pack_start(rotulo(" · ".join(p for p in partes if p), ["ms-dim", "ms-pequeno"], wrap=True),
                             False, False, 0)
            if ativa.incluida:
                botoes.pack_start(botao("Duplicar para editar", "ms-secundario",
                                        ao_clicar=lambda: j.duplicar(ativa)), False, False, 0)
            else:
                botoes.pack_start(botao("Atualizar com a tela", "ms-secundario",
                                        dica="Grava as mudanças que você fez no desktop",
                                        ao_clicar=lambda: j.atualizar(ativa)), False, False, 0)
        else:
            capa.definir(j.app.capas.papel_de_parede_atual())
            texto.pack_start(rotulo(T.SEM_BACKUP_TITULO, ["ms-titulo-hero"]), False, False, 0)
            texto.pack_start(rotulo(T.SEM_BACKUP_TEXTO, ["ms-dim"], wrap=True), False, False, 0)
            botoes.pack_start(botao("Salvar como skin", "ms-primario", ao_clicar=j.salvar_atual), False, False, 0)
        texto.pack_start(botoes, False, False, 0)
        card.pack_start(capa, False, False, 0)
        card.pack_start(texto, True, True, 0)
        self.hero.pack_start(card, True, True, 0)
        self.hero.show_all()


class Galeria(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.filtro = "todas"
        self.busca = busca(self.atualizar)
        self.caixa.pack_start(cabecalho(*T.GALERIA, self.busca), False, False, 0)
        chips = Gtk.Box(spacing=8)
        primeiro = None
        for chave, texto in T.FILTROS:
            b = css(Gtk.RadioButton.new_with_label_from_widget(primeiro, texto), "ms-chip")
            b.set_mode(False)
            primeiro = primeiro or b
            b.connect("toggled", self._filtrou, chave)
            chips.pack_start(b, False, False, 0)
        self.caixa.pack_start(chips, False, False, 0)
        self.grade = grade()
        self.vazio = vazio(*T.VAZIO_GALERIA)
        self.caixa.pack_start(self.grade, False, False, 0)
        self.caixa.pack_start(self.vazio, False, False, 0)

    def _filtrou(self, b, chave):
        if b.get_active():
            self.filtro = chave
            self.atualizar()

    def atualizar(self):
        itens = self.j.app.nuvem.galeria(self.filtro, self.busca.get_text())
        preencher(self.grade, self.vazio, [self.j.card_item(i) for i in itens])
        textos = T.VAZIO_FAVORITAS if self.filtro == "favoritas" else T.VAZIO_GALERIA
        self.vazio.get_children()[0].set_text(textos[0])
        self.vazio.get_children()[1].set_text(textos[1])


class Minhas(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.busca = busca(self.atualizar)
        self.caixa.pack_start(cabecalho(*T.MINHAS, self.busca), False, False, 0)
        self.grade = grade()
        self.vazio = vazio(*T.VAZIO_MINHAS, (T.SALVAR, j.salvar_atual))
        self.caixa.pack_start(self.grade, False, False, 0)
        self.caixa.pack_start(self.vazio, False, False, 0)

    def atualizar(self):
        skins = self.j.app.skins.do_usuario(self.busca.get_text())
        preencher(self.grade, self.vazio, [self.j.card_local(s) for s in skins])


class Detalhe(Pagina):
    def mostrar(self, item):
        j = self.j
        self.item = item
        self.limpar()
        topo = Gtk.Box(spacing=28)
        topo.pack_start(capa_grande(j.app.capas, item), False, False, 0)
        lado = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, valign=Gtk.Align.CENTER)
        if item.oficial:
            lado.pack_start(rotulo("OFICIAL", ["ms-sobrelinha"]), False, False, 0)
        lado.pack_start(rotulo(item.nome, ["ms-titulo-hero"], wrap=True), False, False, 0)
        lado.pack_start(link(f"por {item.autor_nome}", lambda: j.abrir_perfil(item.autor_id),
                             ("ms-autor-mintskins",)), False, False, 0)
        if item.descricao:
            lado.pack_start(rotulo(item.descricao, ["ms-dim"], wrap=True), False, False, 0)
        acoes = Gtk.Box(spacing=8, margin_top=12)
        texto, cb, estilo = j.acao_item(item)
        b = botao(texto, estilo, ao_clicar=cb)
        b.set_sensitive(cb is not None)
        acoes.pack_start(b, False, False, 0)
        acoes.pack_start(BotaoFavorito(item.favorito, lambda v: j.favoritar(item, v), item.favoritos),
                         False, False, 0)
        lado.pack_start(acoes, False, False, 0)
        topo.pack_start(lado, True, True, 0)
        self.caixa.pack_start(topo, False, False, 0)

        gtk_tema, icones = j.app.capas.temas(item)
        linhas = [linha("Autor", None, valor(item.autor_nome, item.oficial)),
                  linha("Tema", None, valor(gtk_tema or "—")),
                  linha("Ícones", None, valor(icones or "—")),
                  linha("Dock", None, valor("Sim" if item.dock else "Não"))]
        if not item.oficial:
            linhas += [linha("Publicada em", None, valor(data_br(item.publicada_em, hora=False))),
                       linha("Downloads", None, valor(str(item.downloads))),
                       linha("Tamanho", None, valor(tamanho_br(item.tamanho)))]
        linhas.append(linha("Favoritos", None, valor(str(item.favoritos))))
        self.caixa.pack_start(grupo("Detalhes", linhas), False, False, 0)
        self.caixa.show_all()

    def atualizar(self):
        if getattr(self, "item", None):
            try:
                self.mostrar(self.j.app.nuvem.item(self.item.id))
            except Exception:  # noqa: BLE001 — item removido enquanto estava aberto
                self.j.voltar()


class Perfil(Detalhe):
    def mostrar(self, perfil):
        j = self.j
        self.perfil = perfil
        self.limpar()
        topo = Gtk.Box(spacing=20)
        topo.pack_start(Avatar(perfil.iniciais, grande=True), False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        nome = Gtk.Box(spacing=10)
        nome.pack_start(rotulo(perfil.nome, ["ms-titulo-hero"]), False, False, 0)
        if perfil.oficial:
            nome.pack_start(css(Gtk.Label(label="Oficial"), "ms-badge", "ms-destaque"), False, False, 0)
        textos.pack_start(nome, False, False, 0)
        resumo = [contar(len(perfil.itens), "skin publicada", "skins publicadas")]
        if perfil.desde:
            resumo.append(f"na galeria desde {data_br(perfil.desde, hora=False)}")
        if not perfil.oficial:
            resumo.append(contar(perfil.downloads, "download", "downloads"))
        textos.pack_start(rotulo(" · ".join(resumo), ["ms-dim"]), False, False, 0)
        topo.pack_start(textos, True, True, 0)
        self.caixa.pack_start(topo, False, False, 0)
        g = grade()
        v = vazio("Nenhuma skin publicada", "Quando publicar, as skins aparecem aqui.")
        self.caixa.pack_start(g, False, False, 0)
        self.caixa.pack_start(v, False, False, 0)
        self.caixa.show_all()
        preencher(g, v, [j.card_item(i) for i in perfil.itens])

    def atualizar(self):
        if getattr(self, "perfil", None):
            p = self.j.app.nuvem.perfil(self.perfil.id)
            self.mostrar(p) if p else self.j.voltar()


class Conta(Pagina):
    def atualizar(self):
        self.limpar()
        conta = self.j.conta
        self.caixa.pack_start(cabecalho(*T.CONTA), False, False, 0)
        grades = self._logado(conta) if conta else self._entrar()
        self.caixa.pack_start(rotulo(T.NUVEM_LOCAL, ["ms-legal"], wrap=True), False, False, 0)
        self.caixa.show_all()
        for g, v, cards in grades:
            preencher(g, v, cards)

    def _entrar(self):
        cartao = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14), "ms-grupo", "ms-grupo-linha")
        cartao.set_halign(Gtk.Align.START)
        cartao.set_size_request(440, -1)
        formas = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vhomogeneous=False,
                           interpolate_size=True)
        seletor = Gtk.StackSwitcher(stack=formas, halign=Gtk.Align.START)
        cartao.pack_start(seletor, False, False, 0)
        formas.add_titled(self._formulario(False), "entrar", "Entrar")
        formas.add_titled(self._formulario(True), "criar", "Criar conta")
        cartao.pack_start(formas, False, False, 0)
        self.caixa.pack_start(cartao, False, False, 0)
        return []

    def _formulario(self, criar):
        caixa = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=6)
        campos = {}
        for chave, rot, senha in ((("nome", "Nome", False),) if criar else ()) + (
                ("email", "E-mail", False), ("senha", "Senha", True)):
            caixa.pack_start(rotulo(rot, ["ms-dim", "ms-pequeno"]), False, False, 0)
            e = css(Gtk.Entry(visibility=not senha, activates_default=False), "ms-campo")
            if senha:
                e.set_input_purpose(Gtk.InputPurpose.PASSWORD)
                e.set_placeholder_text("pelo menos 8 caracteres" if criar else "")
            elif chave == "email":
                e.set_input_purpose(Gtk.InputPurpose.EMAIL)
            campos[chave] = e
            caixa.pack_start(e, False, False, 0)
        erro = rotulo("", ["ms-erro", "ms-pequeno"], wrap=True)
        caixa.pack_start(erro, False, False, 0)
        acao = botao("Criar conta" if criar else "Entrar", "ms-primario",
                     ao_clicar=lambda: self.j.entrar(criar, {k: e.get_text() for k, e in campos.items()}, erro))
        acao.set_halign(Gtk.Align.START)
        for e in campos.values():
            e.connect("activate", lambda _e: acao.clicked())
        caixa.pack_start(acao, False, False, 4)
        erro.set_no_show_all(True)
        return caixa

    def _logado(self, conta):
        j = self.j
        topo = css(Gtk.Box(spacing=18), "ms-hero")
        topo.pack_start(Avatar(conta.iniciais, grande=True), False, False, 0)
        textos = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        textos.pack_start(rotulo(conta.nome, ["ms-titulo-hero"]), False, False, 0)
        textos.pack_start(rotulo(f"{conta.email} · desde {data_br(conta.criada_em, hora=False)}", ["ms-dim"]),
                          False, False, 0)
        topo.pack_start(textos, True, True, 0)
        botoes = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
        botoes.pack_start(botao("Meu perfil", "ms-secundario", ao_clicar=lambda: j.abrir_perfil(conta.id)),
                          False, False, 0)
        botoes.pack_start(botao("Sair", "ms-fantasma", ao_clicar=j.sair), False, False, 0)
        topo.pack_end(botoes, False, False, 0)
        self.caixa.pack_start(topo, False, False, 0)
        grades = []
        for titulo, itens, textos_vazio in (("Na minha conta", j.app.nuvem.da_conta(), T.VAZIO_NUVEM),
                                            ("Favoritas", j.app.nuvem.favoritas(), T.VAZIO_FAVORITAS)):
            self.caixa.pack_start(rotulo(titulo, ["ms-titulo-secao"]), False, False, 0)
            g, v = grade(), vazio(*textos_vazio)
            self.caixa.pack_start(g, False, False, 0)
            self.caixa.pack_start(v, False, False, 0)
            grades.append((g, v, [j.card_item(i, dono=titulo == "Na minha conta") for i in itens]))
        return grades


class Preferencias(Pagina):
    def __init__(self, j):
        super().__init__(j)
        prefs = j.app.skins.preferencias()
        self.caixa.pack_start(cabecalho(T.PREFERENCIAS[0]), False, False, 0)
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

        self.caixa.pack_start(grupo("Atualizações", [
            linha("Procurar versões novas", "Verifica no GitHub ao abrir o MintSkins.",
                  self._chave(prefs, "verificar_atualizacoes")),
            linha(f"Versão instalada: {__version__}", None,
                  botao("Verificar agora", "ms-secundario", ao_clicar=lambda: j.verificar_versao(True))),
        ]), False, False, 0)

        self.caixa.pack_start(grupo("Avançado", [
            linha("Pasta das minhas skins", None,
                  botao("Abrir", "ms-secundario", ao_clicar=lambda: j.abrir_pasta(j.app.skins.pasta_minhas_skins()))),
            linha("Tela de login original", "Desfaz o visual aplicado na tela de login.",
                  botao("Restaurar", "ms-secundario", ao_clicar=j.restaurar_login)),
        ]), False, False, 0)

    def _chave(self, prefs, campo):
        sw = Gtk.Switch(active=getattr(prefs, campo))
        sw.connect("notify::active", lambda s, _p: self.j.mudar_preferencia(campo, s.get_active()))
        return sw


class Sobre(Pagina):
    def __init__(self, j):
        super().__init__(j)
        self.caixa.set_halign(Gtk.Align.CENTER)
        self.caixa.set_size_request(640, -1)
        logo = j.logo(340)
        logo.set_margin_top(12)
        self.caixa.pack_start(logo, False, False, 0)
        self.caixa.pack_start(rotulo(T.SLOGAN, ["ms-dim"], xalign=0.5), False, False, 0)
        self.caixa.pack_start(rotulo("Sobre nós", ["ms-titulo-secao"]), False, False, 0)
        self.caixa.pack_start(rotulo(T.SOBRE_NOS, ["ms-sobre-texto"], wrap=True), False, False, 0)
        self.caixa.pack_start(grupo(None, [
            linha("Proprietário", None, valor(T.PROPRIETARIO, destaque=True)),
            linha("Versão", None, valor(__version__)),
            linha("Plataforma", None, valor("Linux Mint · Cinnamon")),
            linha("Código", None, botao("Abrir no GitHub", "ms-secundario", icone_nome="web-browser-symbolic",
                                        ao_clicar=lambda: j.abrir_url(T.URL_PROJETO))),
        ]), False, False, 0)
        self.caixa.pack_start(rotulo(T.LEGAL, ["ms-legal"], xalign=0.5, wrap=True), False, False, 0)

