"""Adaptador do desktop Cinnamon: captura e aplica o visual (porta Desktop)."""
import json
import os
import re
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path

from ..dominio.erros import MintSkinsErro, SkinInvalida
from ..dominio.preferencias import Preferencias
from ..dominio.skin import Skin
from . import gsettings
from .caminhos import (AUTOSTART, AUTOSTART_SISTEMA, HOME, INSTALADOS, LOGIN_HELPER, PASTA_FONTES, PLANK_CFG,
                       SPICES, atualizar_cache_de_fontes)
from .perfil import (CHAVES_FONTE, PLANK, TEMAS_ICONE_SISTEMA, aplicar_perfil, caminho_de_uri,
                     capturar_perfil, generalizar, ler_perfil, perfil_da_skin, resetar_ausentes,
                     sem_aspas, substituidor, valor_no_perfil)


def _nada(*_a, **_k):
    pass


def copiar(origem, destino):
    origem, destino = Path(origem), Path(destino)
    if destino.is_symlink() or destino.is_file():
        destino.unlink()
    elif destino.exists():
        shutil.rmtree(destino)
    if origem.is_dir() and not origem.is_symlink():
        shutil.copytree(origem, destino, symlinks=True)
    else:
        shutil.copy2(origem, destino, follow_symlinks=False)


def sincronizar(origem, destino):
    """Substitui no destino cada item que vem na skin (garante a versao dela)."""
    origem, destino = Path(origem), Path(destino)
    if not origem.is_dir():
        return 0
    destino.mkdir(parents=True, exist_ok=True)
    n = 0
    for item in sorted(origem.iterdir()):
        copiar(item, destino / item.name)
        n += 1
    return n


def _irmaos_por_link(pasta):
    """Temas 'irmaos' dos quais este depende via symlink (MacTahoe-dark -> ../MacTahoe)."""
    pasta = Path(pasta)
    base = pasta.parent
    nomes = set()
    for raiz, dirs, arqs in os.walk(pasta):
        for n in dirs + arqs:
            p = Path(raiz, n)
            if not p.is_symlink():
                continue
            alvo = Path(os.path.normpath(Path(raiz, os.readlink(p))))
            try:
                rel = alvo.relative_to(base)
            except ValueError:
                continue
            if rel.parts and rel.parts[0] != pasta.name:
                nomes.add(rel.parts[0])
    return sorted(nomes)


def _copiar_tema(nome, destino, log):
    if not nome or (destino / nome).exists():
        return
    for base in (Path(HOME, ".themes"), Path(HOME, ".local/share/themes")):
        if (base / nome).is_dir():
            copiar(base / nome, destino / nome)
            log(f"tema {nome}")
            for h in _irmaos_por_link(base / nome):
                _copiar_tema(h, destino, log)
            return
    # so existe em /usr/share: vem com o sistema, nao precisa ir na skin


def _copiar_icone(nome, destino, log, sistema=False):
    if not nome or nome in TEMAS_ICONE_SISTEMA or (destino / nome).exists():
        return
    src = None
    for base in (Path(HOME, ".local/share/icons"), Path(HOME, ".icons")):
        if (base / nome).is_dir():
            src = base / nome
            break
    if src is None and sistema and Path("/usr/share/icons", nome).is_dir():
        src = Path("/usr/share/icons", nome)
    if src is None:
        return
    copiar(src, destino / nome)
    log(f"icones {nome}")
    try:
        for l in (src / "index.theme").read_text(errors="ignore").splitlines():
            if l.startswith("Inherits="):
                for h in l.split("=", 1)[1].split(","):
                    _copiar_icone(h.strip(), destino, log)
                break
    except OSError:
        pass
    for h in _irmaos_por_link(src):
        _copiar_icone(h, destino, log, sistema=True)


def _familias_de_fonte(perfil):
    fams = set()
    for _, k, v in ler_perfil(perfil):
        if k not in CHAVES_FONTE:
            continue
        f = sem_aspas(v)
        f = re.sub(r" [^ ]*=[^ ]*", "", f)
        f = re.sub(r" [0-9.]+$", "", f)
        f = re.sub(r" (Bold|Italic|Medium|Light|Semibold|Regular|Oblique)$", "", f, flags=re.I)
        if f:
            fams.add(f)
    return sorted(fams)


def _copiar_fontes(perfil, destino, log):
    """So fontes instaladas pelo usuario: as do sistema existem em qualquer Mint."""
    for fam in _familias_de_fonte(perfil):
        r = subprocess.run(["fc-list", fam, "--format=%{file}\n"], capture_output=True, text=True)
        n = 0
        for f in r.stdout.splitlines():
            if f.startswith(HOME + "/") and os.path.isfile(f) and not f.lower().endswith((".woff", ".woff2")):
                alvo = destino / os.path.basename(f)
                if not alvo.exists():
                    shutil.copy2(f, alvo)
                n += 1
        if n:
            log(f"fonte {fam} ({n} arquivos)")


def _uuids_ativos(perfil):
    uuids = set()
    exts = valor_no_perfil(perfil, "org.cinnamon", "enabled-extensions") or ""
    uuids_ext = set(re.findall(r"[^\[\]',\s]+@[^\[\]',\s]+", exts))
    apps = valor_no_perfil(perfil, "org.cinnamon", "enabled-applets") or ""
    uuids_app = set()
    for item in re.findall(r"'([^']+)'", apps):
        partes = item.split(":")
        if len(partes) >= 4:
            uuids_app.add(partes[3])
    uuids |= uuids_ext | uuids_app
    return uuids_ext, uuids_app


def generalizar_spices(pasta_spices, pasta_arquivos, procurar_em=()):
    """Troca caminhos pessoais nos JSON dos applets por @@HOME@@/@@PACOTE@@.

    Arquivos pessoais referenciados (ex.: icone do Cinnamenu) sao copiados para
    pasta_arquivos, para viajarem junto com a skin.
    """
    pasta_arquivos = Path(pasta_arquivos)
    pasta_arquivos.mkdir(parents=True, exist_ok=True)
    usados = {}

    def trata(s):
        if not isinstance(s, str):
            return s
        pref, p = "", s
        if s.startswith("file://"):
            pref, p = "file://", urllib.parse.unquote(s[7:])
        if p == HOME:
            return pref + "@@HOME@@"
        if not p.startswith(HOME + "/"):
            return s
        if not os.path.isfile(p):
            for d in procurar_em:
                cand = os.path.join(d, os.path.basename(p))
                if os.path.isfile(cand):
                    p = cand
                    break
        if os.path.isfile(p):
            base = os.path.basename(p)
            nome, i = base, 1
            while nome in usados and usados[nome] != p:
                nome = f"{i}_{base}"
                i += 1
            usados[nome] = p
            alvo = pasta_arquivos / nome
            if not alvo.exists():
                shutil.copy2(p, alvo)
            return pref + "@@PACOTE@@/arquivos/" + nome
        return pref + "@@HOME@@" + p[len(HOME):]

    def anda(o):
        if isinstance(o, dict):
            return {k: anda(v) for k, v in o.items()}
        if isinstance(o, list):
            return [anda(v) for v in o]
        return trata(o)

    for raiz, _, arqs in os.walk(pasta_spices):
        for a in arqs:
            if not a.endswith(".json"):
                continue
            c = Path(raiz, a)
            try:
                dados = json.loads(c.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            c.write_text(json.dumps(anda(dados), indent=4, ensure_ascii=False), encoding="utf-8")
    return len(usados)


def _ler_desktop(arquivo):
    """Chaves do grupo [Desktop Entry] de um .desktop."""
    dados, no_grupo = {}, False
    try:
        linhas = Path(arquivo).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return dados
    for l in linhas:
        l = l.strip()
        if l.startswith("["):
            no_grupo = l == "[Desktop Entry]"
        elif no_grupo and "=" in l:
            k, v = l.split("=", 1)
            dados[k.strip()] = v.strip()
    return dados


def _habilitada(dados):
    # "Aplicativos de inicializacao" desliga gravando enabled=false, sem apagar o arquivo
    return dados.get("Hidden", "").lower() != "true" \
        and dados.get("X-GNOME-Autostart-enabled", "true").lower() != "false"


def _autostarts_do_plank():
    """{nome: (arquivo, dados)} das entradas de inicializacao que abrem o Plank.

    Qualquer nome de arquivo, do usuario ou do sistema; a do usuario sobrepoe a de mesmo nome.
    """
    entradas = {}
    for pasta in (AUTOSTART_SISTEMA, AUTOSTART):
        if pasta.is_dir():
            for f in pasta.glob("*.desktop"):
                entradas[f.name] = (f, _ler_desktop(f))
    return {n: (f, d) for n, (f, d) in entradas.items()
            if any(os.path.basename(p) == "plank" for p in d.get("Exec", "").split())}


def _dock_ativo():
    return any(_habilitada(d) for _, d in _autostarts_do_plank().values())


def _tirar_plank_da_inicializacao(exceto=None):
    """Apaga as entradas do usuario e anula (Hidden=true) as do sistema."""
    for nome, (f, _) in _autostarts_do_plank().items():
        if nome == exceto:
            continue
        if f.parent == AUTOSTART:
            f.unlink(missing_ok=True)
        if (AUTOSTART_SISTEMA / nome).is_file():
            AUTOSTART.mkdir(parents=True, exist_ok=True)
            (AUTOSTART / nome).write_text("[Desktop Entry]\nType=Application\nName=Plank\n"
                                          "Exec=plank\nHidden=true\n", encoding="utf-8")


def _instalar_recursos(skin, log):
    sincronizar(skin / "temas", Path(HOME, ".themes"))
    sincronizar(skin / "icones", Path(HOME, ".local/share/icons"))
    sincronizar(skin / "extensoes", Path(HOME, ".local/share/cinnamon/extensions"))
    sincronizar(skin / "applets", Path(HOME, ".local/share/cinnamon/applets"))
    if (skin / "icones").is_dir():
        for t in (skin / "icones").iterdir():
            subprocess.run(["gtk-update-icon-cache", "-q", "-f", "-t",
                            str(Path(HOME, ".local/share/icons", t.name))], capture_output=True)
    if (skin / "plank/temas").is_dir():
        dst = Path(HOME, ".local/share/plank/themes")
        dst.mkdir(parents=True, exist_ok=True)
        for t in (skin / "plank/temas").iterdir():
            if not (dst / t.name).exists():
                copiar(t, dst / t.name)
    if (skin / "fontes").is_dir():
        dst = PASTA_FONTES
        dst.mkdir(parents=True, exist_ok=True)
        novas = 0
        for f in (skin / "fontes").iterdir():
            # woff/woff2 sao fontes de site: o fontconfig indexa, mas apps Chromium/Electron quebram nelas
            if not f.is_file() or f.suffix.lower() in (".woff", ".woff2"):
                continue
            alvo = dst / f.name
            if not alvo.exists() or alvo.stat().st_size != f.stat().st_size:
                shutil.copy(f, alvo)   # sem copy2: data nova, senao o fontconfig acha que o cache ainda vale
                novas += 1
        atualizar_cache_de_fontes()
        if novas:
            log(f"{novas} fontes instaladas")


def _aplicar_spices(skin, subst):
    origem = skin / "spices"
    if not origem.is_dir():
        return
    for d in origem.iterdir():
        if not d.is_dir():
            continue
        alvo = SPICES / d.name
        if alvo.exists():
            shutil.rmtree(alvo)
        alvo.mkdir(parents=True)
        for f in d.iterdir():
            if f.is_file():
                (alvo / f.name).write_text(subst(f.read_text(encoding="utf-8", errors="ignore")),
                                           encoding="utf-8")


def _aplicar_papel_de_parede(skin, instalada):
    conf = skin / "papel_de_parede.conf"
    if not conf.is_file():
        return False
    dados = dict(l.split("\t", 1) for l in conf.read_text(encoding="utf-8").splitlines() if "\t" in l)
    arq = instalada / "arquivos" / dados.get("arquivo", "")
    if not dados.get("arquivo") or not arq.is_file():
        return False
    gsettings.definir("org.cinnamon.desktop.background", "picture-uri", "'" + arq.resolve().as_uri() + "'")
    if dados.get("picture-options"):
        gsettings.definir("org.cinnamon.desktop.background", "picture-options", dados["picture-options"])
    return True


def _iniciar_desanexado(cmd):
    subprocess.Popen(cmd, cwd=HOME, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def _plank(skin, dock, subst, log):
    subprocess.run(["pkill", "-x", "plank"], capture_output=True)
    if (skin / "plank/dock1").is_dir():
        if (PLANK_CFG / "dock1").exists():
            shutil.rmtree(PLANK_CFG / "dock1")
        shutil.copytree(skin / "plank/dock1", PLANK_CFG / "dock1", symlinks=True)
        for f in (PLANK_CFG / "dock1").rglob("*.dockitem"):
            f.write_text(subst(f.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
    elif (skin / "plank/launchers").is_dir():
        dst = PLANK_CFG / "dock1/launchers"
        dst.mkdir(parents=True, exist_ok=True)
        for f in dst.glob("*.dockitem"):
            f.unlink()
        for f in (skin / "plank/launchers").glob("*.dockitem"):
            (dst / f.name).write_text(subst(f.read_text(encoding="utf-8", errors="ignore")),
                                      encoding="utf-8")
    if not dock:
        _tirar_plank_da_inicializacao()
        log("dock desligado")
        return
    if not shutil.which("plank"):
        log("aviso: Plank nao instalado — instale com: sudo apt install plank")
        return
    autostart = AUTOSTART / "plank.desktop"
    _tirar_plank_da_inicializacao(exceto=autostart.name)   # evita dois Plank no login
    AUTOSTART.mkdir(parents=True, exist_ok=True)
    autostart.write_text("[Desktop Entry]\nType=Application\nName=Plank\nExec=plank\n"
                         "Icon=plank\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
    time.sleep(0.5)
    _iniciar_desanexado(["plank"])
    log("dock Plank ativo")


def recarregar_cinnamon():
    if subprocess.run(["pgrep", "-x", "cinnamon"], capture_output=True).returncode == 0 \
            and os.environ.get("DISPLAY"):
        _iniciar_desanexado(["cinnamon", "--replace"])
        return True
    return False


class DesktopCinnamon:
    """Implementa a porta Desktop para o Linux Mint Cinnamon."""

    def verificar(self):
        gsettings.exigir_cinnamon()

    def capturar(self, destino, leve=False, progresso=_nada):
        """Grava o visual da tela em `destino` (pasta vazia). Devolve se o dock esta ligado.

        leve=True guarda so configuracoes (sem temas/icones/fontes): usado no
        "desfazer", ja que os arquivos da skin anterior continuam instalados.
        """
        tmp = Path(destino)
        for sub in ("temas", "icones", "fontes", "extensoes", "applets", "spices", "arquivos",
                    "plank/launchers", "plank/temas"):
            (tmp / sub).mkdir(parents=True, exist_ok=True)
        log = lambda t: progresso(t)

        progresso("Lendo configurações do desktop", 0.05)
        perfil = tmp / "perfil.conf"
        capturar_perfil(perfil)
        perfil.write_text(generalizar(perfil.read_text(encoding="utf-8")), encoding="utf-8")
        v = lambda s, k: sem_aspas(valor_no_perfil(perfil, s, k))

        if not leve:
            progresso("Copiando temas", 0.15)
            for s, k in (("org.cinnamon.desktop.interface", "gtk-theme"),
                         ("org.cinnamon.desktop.wm.preferences", "theme"),
                         ("org.cinnamon.theme", "name")):
                _copiar_tema(v(s, k), tmp / "temas", log)
            progresso("Copiando ícones e cursor", 0.3)
            _copiar_icone(v("org.cinnamon.desktop.interface", "icon-theme"), tmp / "icones", log)
            _copiar_icone(v("org.cinnamon.desktop.interface", "cursor-theme"), tmp / "icones", log)
            progresso("Copiando fontes", 0.55)
            _copiar_fontes(perfil, tmp / "fontes", log)

        progresso("Copiando applets e extensões", 0.65)
        exts, apps = _uuids_ativos(perfil)
        for uuid in sorted(exts | apps):
            tipo, dst = ("extensions", "extensoes") if uuid in exts else ("applets", "applets")
            src = Path(HOME, ".local/share/cinnamon", tipo, uuid)
            if not leve and src.is_dir():
                copiar(src, tmp / dst / uuid)
            if (SPICES / uuid).is_dir():
                copiar(SPICES / uuid, tmp / "spices" / uuid)
        generalizar_spices(tmp / "spices", tmp / "arquivos", procurar_em=[str(INSTALADOS)])

        progresso("Copiando dock", 0.8)
        launchers = PLANK_CFG / "dock1/launchers"
        if launchers.is_dir():
            for f in launchers.glob("*.dockitem"):
                (tmp / "plank/launchers" / f.name).write_text(
                    generalizar(f.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
        tp = v(PLANK, "theme")
        if not leve and tp and Path(HOME, ".local/share/plank/themes", tp).is_dir():
            copiar(Path(HOME, ".local/share/plank/themes", tp), tmp / "plank/temas" / tp)

        progresso("Copiando papel de parede", 0.9)
        fundo = caminho_de_uri(gsettings.ler("org.cinnamon.desktop.background", "picture-uri") or "")
        if os.path.isfile(fundo):
            ext = os.path.splitext(fundo)[1] or ".jpg"
            shutil.copy2(fundo, tmp / "arquivos" / f"papel_de_parede{ext}")
            opc = gsettings.ler("org.cinnamon.desktop.background", "picture-options") or "'zoom'"
            (tmp / "papel_de_parede.conf").write_text(
                f"arquivo\tpapel_de_parede{ext}\npicture-options\t{opc}\n", encoding="utf-8")

        for sub in sorted(tmp.rglob("*"), reverse=True):
            if sub.is_dir() and not sub.is_symlink() and not any(sub.iterdir()):
                sub.rmdir()
        progresso("Skin salva", 1.0)
        return _dock_ativo()

    def aplicar(self, skin: Skin, prefs: Preferencias, progresso=_nada):
        pasta = Path(skin.pasta)
        perfil = perfil_da_skin(pasta)
        if perfil is None:
            raise SkinInvalida(f"{pasta} não parece uma skin (falta perfil.conf).")
        avisos = []

        def log(t):
            if t.startswith("aviso"):
                avisos.append(t.removeprefix("aviso: "))
            progresso(t)

        progresso("Instalando temas, ícones e fontes", 0.2)
        _instalar_recursos(pasta, log)

        instalada = INSTALADOS / skin.id
        if (pasta / "arquivos").is_dir() and pasta.resolve() != instalada.resolve():
            instalada.mkdir(parents=True, exist_ok=True)
            if (instalada / "arquivos").exists():
                shutil.rmtree(instalada / "arquivos")
            shutil.copytree(pasta / "arquivos", instalada / "arquivos")
        subst = substituidor(instalada)

        progresso("Aplicando painel e applets", 0.55)
        # applets ANTES do painel: senao o Cinnamon recria as instancias com o padrao
        _aplicar_spices(pasta, subst)
        aplicar_perfil(perfil, subst)
        resetar_ausentes(perfil)
        time.sleep(1)
        _aplicar_spices(pasta, subst)

        if prefs.papel_de_parede:
            progresso("Aplicando papel de parede", 0.7)
            _aplicar_papel_de_parede(pasta, instalada)

        progresso("Ajustando o dock", 0.8)
        _plank(pasta, skin.dock, subst, log)

        if prefs.tela_login:
            progresso("Ajustando a tela de login (pede senha)", 0.88)
            try:
                self._tela_login()
            except MintSkinsErro as e:
                avisos.append(f"tela de login mantida ({e})")

        subprocess.run(["nemo", "-q"], capture_output=True)   # janelas do Nemo guardam icones antigos
        if prefs.recarregar:
            progresso("Recarregando o Cinnamon", 0.95)
            if not recarregar_cinnamon():
                avisos.append("recarregue o Cinnamon com Alt+F2, r, Enter")
        progresso("Pronto", 1.0)
        return avisos

    def corresponde(self, skin: Skin):
        """A skin bate com o que esta na tela? (tema + paineis)"""
        perfil = perfil_da_skin(skin.pasta)
        if not perfil:
            return False
        for s, k in (("org.cinnamon.desktop.interface", "gtk-theme"), ("org.cinnamon", "panels-enabled")):
            if valor_no_perfil(perfil, s, k) != gsettings.ler(s, k):
                return False
        return True

    def restaurar_tela_login(self):
        self._tela_login(restaurar=True)

    @staticmethod
    def _tela_login(restaurar=False):
        """LightDM/slick-greeter, via helper com pkexec (pede senha)."""
        if not os.path.isdir("/etc/lightdm"):
            raise MintSkinsErro("LightDM não encontrado")
        if restaurar:
            args = ["restaurar"]
        else:
            g = lambda k: sem_aspas(gsettings.ler("org.cinnamon.desktop.interface", k))
            fundo = caminho_de_uri(gsettings.ler("org.cinnamon.desktop.background", "picture-uri") or "")
            args = ["aplicar", fundo, g("gtk-theme"), g("icon-theme"), g("cursor-theme"), g("font-name")]
        r = subprocess.run(["pkexec", str(LOGIN_HELPER), *args], capture_output=True, text=True)
        if r.returncode != 0:
            raise MintSkinsErro(r.stderr.strip() or "cancelado")
