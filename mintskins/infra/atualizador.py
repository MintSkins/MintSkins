"""Atualizacoes pelo GitHub Releases (porta Atualizacoes)."""
import hashlib
import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from .. import __version__
from ..dominio.erros import MintSkinsErro
from ..dominio.versao import NovaVersao, mais_nova

REPOSITORIO = "MintSkins/MintSkins"
API = f"https://api.github.com/repos/{REPOSITORIO}"
ORIGENS_PERMITIDAS = (f"https://github.com/{REPOSITORIO}/releases/download/",
                      "https://github.com/PablUoo/MintSkins/releases/download/",   # antes da organizacao
                      "https://objects.githubusercontent.com/")
_PAGINA_RELEASE = re.compile(r"^(https://github\.com/[\w.-]+/[\w.-]+/)releases/")


def origem_da_release(pagina):
    """Se o repositorio mudar de dono ou de nome, o GitHub redireciona a API e a release
    informa o endereco novo: os pacotes dela podem vir de la."""
    m = _PAGINA_RELEASE.match(pagina or "")
    return m.group(1) + "releases/download/" if m else None
TEMPO = 8


def _get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": f"MintSkins/{__version__}"})
    with urllib.request.urlopen(req, timeout=TEMPO) as r:
        return r.read()


class AtualizadorGitHub:
    def __init__(self, versao_atual=__version__):
        self.versao_atual = versao_atual

    def ultima_versao(self):
        """A release mais nova, se for maior que a instalada. Sem rede: None."""
        try:
            rel = json.loads(_get(f"{API}/releases/latest"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise MintSkinsErro(f"Não foi possível verificar atualizações (GitHub: {e.code}).") from e
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
        tag = rel.get("tag_name", "")
        if not mais_nova(tag, self.versao_atual):
            return None
        nova = NovaVersao(versao=tag.lstrip("v"), notas=rel.get("body") or "",
                          pagina=rel.get("html_url", f"https://github.com/{REPOSITORIO}/releases"))
        assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
        deb = next((n for n in assets if n.endswith("_all.deb") and n.startswith(("mintskins_", "mintskin_"))), None)
        if deb:
            nova.pacote_nome, nova.pacote_url = deb, assets[deb]
            if "SHA256SUMS" in assets:
                try:
                    for linha in _get(assets["SHA256SUMS"]).decode().splitlines():
                        partes = linha.split()
                        if len(partes) == 2 and partes[1].lstrip("*") == deb:
                            nova.sha256 = partes[0].lower()
                except (urllib.error.URLError, OSError):
                    pass
        return nova

    def baixar(self, nova, destino, progresso=None):
        """progresso(baixados, total) a cada bloco; total e 0 se o servidor nao informar."""
        origens = ORIGENS_PERMITIDAS + tuple(o for o in [origem_da_release(nova.pagina)] if o)
        if not nova.pacote_url or not nova.pacote_url.startswith(origens):
            raise MintSkinsErro("O pacote desta versão ainda não foi publicado. Tente de novo mais tarde.")
        destino = Path(destino)
        destino.mkdir(parents=True, exist_ok=True)
        arq = destino / Path(nova.pacote_nome).name
        req = urllib.request.Request(nova.pacote_url, headers={"User-Agent": f"MintSkins/{__version__}"})
        h = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=60) as r, open(arq, "wb") as f:
            total, baixados = int(r.headers.get("Content-Length") or 0), 0
            while bloco := r.read(1 << 16):
                h.update(bloco)
                f.write(bloco)
                baixados += len(bloco)
                if progresso:
                    progresso(baixados, total)
        if nova.sha256 and h.hexdigest() != nova.sha256:
            arq.unlink(missing_ok=True)
            raise MintSkinsErro("O pacote baixado não confere com o SHA256 publicado. Atualização cancelada.")
        return arq

    def instalar(self, pacote):
        """Instala o .deb com o apt (pede a senha de administrador)."""
        if not shutil.which("pkexec"):
            raise MintSkinsErro(f"Instale manualmente: sudo apt install {pacote}")
        r = subprocess.run(["pkexec", "apt-get", "install", "-y", "--allow-downgrades",
                            str(Path(pacote).resolve())], capture_output=True, text=True)
        if r.returncode != 0:
            raise MintSkinsErro("A instalação não foi concluída. " + (r.stderr.strip()[-300:] or "Cancelada."))
