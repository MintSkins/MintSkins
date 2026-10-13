"""Perfil de uma skin: as chaves do gsettings que definem visual e layout."""
import re
import urllib.parse
from pathlib import Path

from . import gsettings
from .caminhos import HOME

PLANK = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"

CHAVES = [
    ("org.cinnamon.desktop.interface", "gtk-theme"),
    ("org.cinnamon.desktop.interface", "icon-theme"),
    ("org.cinnamon.desktop.interface", "cursor-theme"),
    ("org.cinnamon.desktop.interface", "cursor-size"),
    ("org.cinnamon.desktop.interface", "font-name"),
    ("org.cinnamon.desktop.interface", "text-scaling-factor"),
    ("org.cinnamon.desktop.wm.preferences", "theme"),
    ("org.cinnamon.desktop.wm.preferences", "button-layout"),
    ("org.cinnamon.desktop.wm.preferences", "titlebar-font"),
    ("org.cinnamon.desktop.wm.preferences", "titlebar-uses-system-font"),
    ("org.cinnamon.theme", "name"),
    ("org.cinnamon", "enabled-applets"),
    ("org.cinnamon", "enabled-extensions"),
    ("org.cinnamon", "next-applet-id"),
    ("org.cinnamon", "panels-enabled"),
    ("org.cinnamon", "panels-height"),
    ("org.cinnamon", "panels-autohide"),
    ("org.cinnamon", "panels-hide-delay"),
    ("org.cinnamon", "panels-show-delay"),
    ("org.cinnamon", "panel-zone-icon-sizes"),
    ("org.cinnamon", "panel-zone-symbolic-icon-sizes"),
    ("org.cinnamon", "panel-zone-text-sizes"),
    ("org.cinnamon", "alttab-switcher-style"),
    ("org.gnome.desktop.interface", "gtk-theme"),
    ("org.gnome.desktop.interface", "icon-theme"),
    ("org.gnome.desktop.interface", "cursor-theme"),
    ("org.gnome.desktop.interface", "font-name"),
    ("org.gnome.desktop.interface", "document-font-name"),
    ("org.gnome.desktop.interface", "monospace-font-name"),
    ("org.nemo.desktop", "font"),
    ("org.cinnamon.desktop.screensaver", "use-custom-format"),
    ("org.cinnamon.desktop.screensaver", "time-format"),
    ("org.cinnamon.desktop.screensaver", "date-format"),
    ("org.cinnamon.desktop.screensaver", "font-time"),
    ("org.cinnamon.desktop.screensaver", "font-date"),
    ("org.cinnamon.desktop.screensaver", "font-message"),
    ("org.cinnamon.desktop.screensaver", "show-info-panel"),
    ("org.cinnamon.desktop.screensaver", "show-album-art"),
    ("org.cinnamon.desktop.screensaver", "floating-widgets"),
    ("org.cinnamon.desktop.screensaver", "allow-media-control"),
    ("org.cinnamon.desktop.screensaver", "show-clock"),
] + [(PLANK, k) for k in (
    "position", "alignment", "items-alignment", "offset", "monitor", "hide-mode",
    "hide-delay", "unhide-delay", "pressure-reveal", "zoom-enabled", "zoom-percent",
    "icon-size", "theme", "dock-items")]

CHAVES_FONTE = {"font-name", "document-font-name", "monospace-font-name", "titlebar-font",
                "font", "font-time", "font-date", "font-message"}
TEMAS_ICONE_SISTEMA = {"hicolor", "default", "Adwaita", "breeze", "breeze-dark", "gnome", "locolor"}


def sem_aspas(v):
    return (v or "").strip("'")


def ler_perfil(arq):
    """Le perfil.conf -> lista de (esquema, chave, valor)."""
    linhas = []
    for l in Path(arq).read_text(encoding="utf-8").splitlines():
        partes = l.split("\t", 2)
        if len(partes) == 3 and partes[0]:
            linhas.append(tuple(partes))
    return linhas


def valor_no_perfil(arq, esquema, chave):
    for s, k, v in ler_perfil(arq):
        if s == esquema and k == chave:
            return v
    return None


def capturar_perfil(arq):
    linhas = []
    for s, k in CHAVES:
        v = gsettings.ler(s, k)
        if v is not None:
            linhas.append(f"{s}\t{k}\t{v}")
    base = "org.cinnamon.desktop.keybindings"
    caminho = "/org/cinnamon/desktop/keybindings/custom-keybindings/"
    lista = gsettings.ler(base, "custom-list")
    if lista is not None:
        linhas.append(f"{base}\tcustom-list\t{lista}")
        for c in re.sub(r"[\[\]',@as ]", " ", lista).split():
            sch = f"{base}.custom-keybinding:{caminho}{c}/"
            for campo in ("name", "command", "binding"):
                v = gsettings.ler(sch, campo)
                if v is not None:
                    linhas.append(f"{sch}\t{campo}\t{v}")
    Path(arq).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return len(linhas)


def aplicar_perfil(arq, subst):
    ok = falhou = 0
    for s, k, v in ler_perfil(arq):
        if gsettings.definir(s, k, subst(v)):
            ok += 1
        else:
            falhou += 1
    return ok, falhou


def resetar_ausentes(arq):
    """Volta ao padrao toda chave da lista que a skin nao define."""
    presentes = {(s, k) for s, k, _ in ler_perfil(arq)}
    for s, k in CHAVES:
        if (s, k) not in presentes and esquema_existe(s):
            gsettings.resetar(s, k)


def substituidor(pasta_instalada):
    def subst(texto):
        return texto.replace("@@PACOTE@@", str(pasta_instalada)).replace("@@HOME@@", HOME)
    return subst


def generalizar(texto):
    return texto.replace(HOME + "/", "@@HOME@@/").replace(HOME + "'", "@@HOME@@'")


def caminho_de_uri(uri):
    uri = sem_aspas(uri)
    if uri.startswith("file://"):
        return urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    return uri


def perfil_da_skin(pasta):
    """perfil.conf (ou perfil_mac.conf, do pacote antigo do mac.sh)."""
    for nome in ("perfil.conf", "perfil_mac.conf"):
        if pasta and Path(pasta, nome).is_file():
            return Path(pasta, nome)
    return None


def valor_da_skin(pasta, esquema, chave):
    perfil = perfil_da_skin(pasta)
    return valor_no_perfil(perfil, esquema, chave) if perfil else None


def papel_de_parede_da_skin(pasta):
    conf = Path(pasta, "papel_de_parede.conf")
    if conf.is_file():
        for l in conf.read_text(encoding="utf-8").splitlines():
            if l.startswith("arquivo\t"):
                p = Path(pasta, "arquivos", l.split("\t", 1)[1])
                if p.is_file():
                    return p
    return None
