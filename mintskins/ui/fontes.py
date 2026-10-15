"""Fontes do app: as mesmas do mintskins.com (Archivo), sem instalar nada no sistema.

Precisa rodar antes de qualquer texto ser desenhado: o Pango le a lista de fontes uma vez so.
"""
import ctypes
import ctypes.util
from pathlib import Path

PASTA = Path(__file__).with_name("marca") / "fontes"


def registrar():
    """Deixa "MintSkins Texto" e "MintSkins Display" visiveis so para este processo."""
    try:
        fc = ctypes.CDLL(ctypes.util.find_library("fontconfig") or "libfontconfig.so.1")
        fc.FcConfigAppFontAddDir.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        return bool(fc.FcConfigAppFontAddDir(None, str(PASTA).encode()))
    except OSError:
        return False  # sem fontconfig o app usa a fonte do sistema
