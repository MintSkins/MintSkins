"""Adaptador do gsettings (linha de comando, igual ao que o usuario usaria)."""
import shutil
import subprocess

from ..dominio.erros import AmbienteIncompativel

_esquemas = None


def _gs(*args):
    r = subprocess.run(["gsettings", *args], capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip()


def esquema_existe(esquema):
    global _esquemas
    if _esquemas is None:
        _, fixos = _gs("list-schemas")
        _, reloc = _gs("list-relocatable-schemas")
        _esquemas = set(fixos.split()) | set(reloc.split())
    return esquema.split(":", 1)[0] in _esquemas


def ler(esquema, chave):
    if not esquema_existe(esquema):
        return None
    ok, v = _gs("get", esquema, chave)
    return v if ok else None


def definir(esquema, chave, valor):
    return _gs("set", esquema, chave, valor)[0]


def resetar(esquema, chave):
    return _gs("reset", esquema, chave)[0]


def exigir_cinnamon():
    if not shutil.which("gsettings"):
        raise AmbienteIncompativel("gsettings não encontrado — o MintSkins é para Linux Mint Cinnamon.")
    if not esquema_existe("org.cinnamon"):
        raise AmbienteIncompativel("Cinnamon não encontrado nesta máquina.")
