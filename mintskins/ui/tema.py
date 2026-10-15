"""Paleta da marca MintSkins, em versao clara e escura."""
from pathlib import Path

MARCA = Path(__file__).with_name("marca")

AMARELO = "#FFC400"
AMARELO_2 = "#FFD84A"
AMARELO_3 = "#FFF1A8"
TINTA = "#0D0D11"

# mesmas cores do mintskins.com
CORES = {
    "escura": {
        "ms_fundo": "#09090C",
        "ms_fundo_2": "#0F0F14",
        "ms_superficie": "#15151C",
        "ms_superficie_2": "#1C1C25",
        "ms_superficie_3": "#272733",
        "ms_borda": "rgba(255,255,255,0.08)",
        "ms_borda_forte": "rgba(255,255,255,0.16)",
        "ms_texto": "#F2F2F5",
        "ms_texto_2": "#A3A3B2",
        "ms_texto_3": "#6C6C7C",
        "ms_destaque": AMARELO,
        "ms_destaque_hover": AMARELO_2,
        "ms_sobre_destaque": TINTA,
        "ms_destaque_texto": AMARELO,
        "ms_destaque_suave": "rgba(255,196,0,0.14)",
        "ms_perigo": "#FF8A8A",
        "ms_sombra": "rgba(0,0,0,0.50)",
    },
    "clara": {
        "ms_fundo": "#F6F5F1",
        "ms_fundo_2": "#EEEDE7",
        "ms_superficie": "#FFFFFF",
        "ms_superficie_2": "#F1F0EA",
        "ms_superficie_3": "#E3E2DA",
        "ms_borda": "rgba(13,13,17,0.10)",
        "ms_borda_forte": "rgba(13,13,17,0.22)",
        "ms_texto": "#0D0D11",
        "ms_texto_2": "#4B4B58",
        "ms_texto_3": "#7A7A88",
        "ms_destaque": AMARELO,
        "ms_destaque_hover": AMARELO_2,
        "ms_sobre_destaque": TINTA,
        "ms_destaque_texto": "#9C6F00",
        "ms_destaque_suave": "rgba(255,196,0,0.20)",
        "ms_perigo": "#B42318",
        "ms_sombra": "rgba(13,13,17,0.10)",
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

