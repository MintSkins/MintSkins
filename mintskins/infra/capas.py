"""Capas das skins (adaptador de imagem, usado pela interface)."""
import hashlib
import re
from pathlib import Path

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf  # noqa: E402

from . import gsettings  # noqa: E402
from .perfil import (caminho_de_uri, papel_de_parede_da_skin, perfil_da_skin,  # noqa: E402
                     sem_aspas, valor_da_skin)

LARGURA, ALTURA = 640, 360


def _cobrir(pix, w, h):
    """Escala e corta o pixbuf para preencher w x h (como 'zoom' do papel de parede)."""
    pw, ph = pix.get_width(), pix.get_height()
    k = max(w / pw, h / ph)
    nw, nh = max(w, round(pw * k)), max(h, round(ph * k))
    pix = pix.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
    return pix.new_subpixbuf((nw - w) // 2, (nh - h) // 2, w, h)


def _v(skin, esquema, chave):
    return valor_da_skin(skin.pasta, esquema, chave)


def _rret(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()


def _paineis(skin):
    """[(posicao, altura)] dos paineis da skin."""
    habil = _v(skin, "org.cinnamon", "panels-enabled") or "['1:0:bottom']"
    alturas = dict(re.findall(r"'(\d+):(\d+)'", _v(skin, "org.cinnamon", "panels-height") or ""))
    out = []
    for pid, pos in re.findall(r"'(\d+):\d+:(\w+)'", habil):
        out.append((pos, int(alturas.get(pid, 40))))
    return out


def _desenhar(skin, destino):
    sup = cairo.ImageSurface(cairo.FORMAT_ARGB32, LARGURA, ALTURA)
    cr = cairo.Context(sup)
    fundo = papel_de_parede_da_skin(skin.pasta)
    pix = None
    if fundo:
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(fundo), LARGURA * 2, -1, True)
        except Exception:
            pix = None
    if pix:
        Gdk.cairo_set_source_pixbuf(cr, _cobrir(pix, LARGURA, ALTURA), 0, 0)
        cr.paint()
    else:
        g = cairo.LinearGradient(0, 0, LARGURA, ALTURA)
        g.add_color_stop_rgb(0, 0.16, 0.42, 0.36)
        g.add_color_stop_rgb(1, 0.08, 0.16, 0.26)
        cr.set_source(g)
        cr.paint()

    escuro = "dark" in (_v(skin, "org.cinnamon.desktop.interface", "gtk-theme") or "").lower()
    cor = (0.10, 0.10, 0.12, 0.72) if escuro else (0.96, 0.96, 0.97, 0.78)
    tinta = (1, 1, 1, 0.85) if escuro else (0.1, 0.1, 0.1, 0.8)
    escala = ALTURA / 1080

    jx, jy, jw, jh = LARGURA * 0.17, ALTURA * 0.19, LARGURA * 0.52, ALTURA * 0.5
    for i in range(6, 0, -1):
        cr.set_source_rgba(0, 0, 0, 0.05)
        _rret(cr, jx - i, jy - i + 4, jw + 2 * i, jh + 2 * i, 10 + i)
        cr.fill()
    fundo_j = (0.16, 0.16, 0.18) if escuro else (0.97, 0.97, 0.98)
    barra_j = (0.22, 0.22, 0.25) if escuro else (0.89, 0.89, 0.91)
    cr.set_source_rgb(*fundo_j)
    _rret(cr, jx, jy, jw, jh, 10)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.12) if escuro else cr.set_source_rgba(0, 0, 0, 0.12)
    cr.set_line_width(1)
    cr.stroke()
    cr.save()
    _rret(cr, jx, jy, jw, jh, 10)
    cr.clip()
    cr.set_source_rgb(*barra_j)
    cr.rectangle(jx, jy, jw, 24)
    cr.fill()
    cr.set_source_rgba(*tinta[:3], 0.10)            # "conteudo" da janela
    cr.rectangle(jx, jy + 24, jw * 0.26, jh - 24)
    cr.fill()
    for i in range(4):
        cr.set_source_rgba(*tinta[:3], 0.16)
        _rret(cr, jx + jw * 0.31, jy + 40 + i * 22, jw * (0.55 - 0.08 * (i % 2)), 9, 4)
        cr.fill()
    cr.restore()
    botoes = (_v(skin, "org.cinnamon.desktop.wm.preferences", "button-layout") or "").strip("'")
    esquerda = botoes.split(":")[0].strip() != ""
    tema = (_v(skin, "org.cinnamon.desktop.wm.preferences", "theme") or "").lower()
    estilo_mac = any(t in tema for t in ("mac", "whitesur", "tahoe"))
    cores = [(1, .37, .34), (1, .74, .18), (.16, .78, .25)] if estilo_mac else [(*tinta[:3],)] * 3
    for i, c in enumerate(cores):
        x = jx + 14 + i * 14 if esquerda else jx + jw - 14 - i * 16
        cr.set_source_rgba(*c, 1 if estilo_mac else 0.55)
        cr.arc(x, jy + 12, 4.5 if estilo_mac else 3.5, 0, 6.2832)
        cr.fill()

    for pos, h in _paineis(skin):
        h = max(10, h * escala * 1.6)
        cr.set_source_rgba(*cor)
        if pos in ("top", "bottom"):
            y = 0 if pos == "top" else ALTURA - h
            cr.rectangle(0, y, LARGURA, h)
            cr.fill()
            cr.set_source_rgba(*tinta)
            for i in range(3):
                cr.rectangle(10 + i * 18, y + h / 2 - 2, 12, 4)
            cr.rectangle(LARGURA - 46, y + h / 2 - 2, 36, 4)
            cr.fill()
        else:
            x = 0 if pos == "left" else LARGURA - h
            cr.rectangle(x, 0, h, ALTURA)
            cr.fill()

    if skin.dock:
        n, lado = 7, 26
        w = n * lado + 16
        x, y = (LARGURA - w) / 2, ALTURA - lado - 22
        cr.set_source_rgba(1, 1, 1, 0.28)
        _rret(cr, x, y, w, lado + 12, 12)
        cr.fill()
        cores = [(.2, .6, 1), (1, .5, .2), (.3, .8, .4), (.9, .3, .4), (.6, .4, 1), (1, .8, .2), (.5, .5, .55)]
        for i, c in enumerate(cores):
            cr.set_source_rgb(*c)
            _rret(cr, x + 8 + i * lado + 2, y + 6, lado - 4, lado - 4, 6)
            cr.fill()
    sup.write_to_png(str(destino))


def capa_propria(skin):
    c = Path(skin.pasta, "capa.png") if skin.pasta else None
    return c if c and c.is_file() else None


class GeradorCapas:
    def __init__(self, cache):
        self.cache = Path(cache)

    def capa(self, skin):
        """Caminho de uma imagem de capa para a skin (gera e guarda em cache)."""
        propria = capa_propria(skin)
        if propria:
            return propria
        self.cache.mkdir(parents=True, exist_ok=True)
        perfil = perfil_da_skin(skin.pasta)
        chave = f"{skin.pasta}|{perfil.stat().st_mtime if perfil else 0}|{skin.dock}|v3"
        destino = self.cache / (hashlib.sha1(chave.encode()).hexdigest()[:16] + ".png")
        if not destino.exists():
            _desenhar(skin, destino)
        return destino

    @staticmethod
    def temas(skin):
        """(tema GTK, tema de icones) da skin, para mostrar na tela."""
        return tuple(sem_aspas(_v(skin, "org.cinnamon.desktop.interface", k))
                     for k in ("gtk-theme", "icon-theme"))

    @staticmethod
    def papel_de_parede_atual():
        uri = gsettings.ler("org.cinnamon.desktop.background", "picture-uri") or ""
        return caminho_de_uri(uri) or None

    @staticmethod
    def capturar_tela(destino, largura=1280):
        return capturar_tela(destino, largura)


def capturar_tela(destino, largura=1280):
    """Screenshot da tela inteira, reduzido. Devolve True se conseguiu."""
    raiz = Gdk.get_default_root_window()
    if raiz is None:
        return False
    w, h = raiz.get_width(), raiz.get_height()
    pix = Gdk.pixbuf_get_from_window(raiz, 0, 0, w, h)
    if pix is None:
        return False
    pix = _cobrir(pix, largura, round(largura * 9 / 16)) if w / h != 16 / 9 else \
        pix.scale_simple(largura, round(largura * h / w), GdkPixbuf.InterpType.BILINEAR)
    pix.savev(str(destino), "png", [], [])
    return True
