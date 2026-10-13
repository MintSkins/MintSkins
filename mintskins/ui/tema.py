"""Paleta da marca MintSkins, em versao clara e escura, e o visual fixo do app."""
from pathlib import Path

from gi.repository import GLib, Gtk

MARCA = Path(__file__).with_name("marca")

AMARELO = "#FFC400"
AMARELO_2 = "#FFD84A"
AMARELO_3 = "#FFF1A8"
TINTA = "#14151F"

CORES = {
    "escura": {
        "ms_fundo": TINTA,
        "ms_lateral": "#191A26",
        "ms_superficie": "#1F2030",
        "ms_superficie_2": "#2A2B3D",
        "ms_borda": "rgba(255,255,255,0.08)",
        "ms_texto": "#F4F4F7",
        "ms_texto_2": "#A3A5B8",
        "ms_destaque": AMARELO,
        "ms_destaque_hover": AMARELO_2,
        "ms_sobre_destaque": TINTA,
        "ms_destaque_texto": AMARELO,
        "ms_destaque_suave": "rgba(255,196,0,0.14)",
        "ms_perigo": "#FF6B6B",
        "ms_sombra": "rgba(0,0,0,0.45)",
    },
    "clara": {
        "ms_fundo": "#F7F6F1",
        "ms_lateral": "#FFFFFF",
        "ms_superficie": "#FFFFFF",
        "ms_superficie_2": "#EFEEE7",
        "ms_borda": "rgba(20,21,31,0.10)",
        "ms_texto": TINTA,
        "ms_texto_2": "#5C5E6E",
        "ms_destaque": AMARELO,
        "ms_destaque_hover": AMARELO_2,
        "ms_sobre_destaque": TINTA,
        "ms_destaque_texto": "#8A5D00",
        "ms_destaque_suave": "rgba(255,196,0,0.20)",
        "ms_perigo": "#C62828",
        "ms_sombra": "rgba(20,21,31,0.10)",
    },
}


def css(variante):
    c = CORES[variante]
    cores = "\n".join(f"@define-color {k} {v};" for k, v in c.items())
    # cor do texto de exemplo dos campos (o tema macOS usa laranja)
    cores += f"\n@define-color placeholder_text_color {c['ms_texto_2']};"
    return cores + "\n" + Path(__file__).with_name("style.css").read_text(encoding="utf-8")


def logo(variante):
    return MARCA / ("logo-escuro.svg" if variante == "escura" else "logo-claro.svg")


SIMBOLO = MARCA / "simbolo.svg"
SINO = MARCA / "sino-symbolic.svg"


# O app nao veste a skin do desktop (botoes de janela do macOS, icones, etc.):
# so neste processo, usa sempre o visual padrao do GTK. O sistema nao muda.
FIXOS = {"gtk-theme-name": "Adwaita", "gtk-icon-theme-name": "Adwaita",
         "gtk-decoration-layout": "menu:minimize,maximize,close"}
SISTEMA = {}


def fixar_visual(ao_mudar_tema=None):
    """Guarda o visual do sistema (para a aparencia automatica) e fixa o do app.
    Quando a skin do desktop muda, o GTK reescreve os valores; aqui voltam ao padrao."""
    cfg = Gtk.Settings.get_default()
    SISTEMA["escuro"] = cfg.props.gtk_application_prefer_dark_theme

    def fixar(_cfg=None, _spec=None, prop=None):
        valor = cfg.get_property(prop)
        if valor == FIXOS[prop]:
            return
        SISTEMA[prop] = valor
        cfg.set_property(prop, FIXOS[prop])
        if prop == "gtk-theme-name" and ao_mudar_tema and _spec is not None:
            GLib.idle_add(ao_mudar_tema)

    for prop in FIXOS:
        fixar(prop=prop)
        cfg.connect(f"notify::{prop}", fixar, prop)
