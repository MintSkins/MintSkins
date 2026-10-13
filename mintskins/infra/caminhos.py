"""Onde o MintSkins le e grava as coisas."""
from pathlib import Path

HOME = str(Path.home())
DADOS = Path(HOME, ".local/share/mintskins")
SKINS_USUARIO = DADOS / "skins"
INSTALADOS = DADOS / "instalados"
DESFAZER = DADOS / "desfazer"
NUVEM_LOCAL = DADOS / "nuvem"
CONFIG = Path(HOME, ".config/mintskins")
CACHE = Path(HOME, ".cache/mintskins")

SPICES = Path(HOME, ".config/cinnamon/spices")
PLANK_CFG = Path(HOME, ".config/plank")
AUTOSTART = Path(HOME, ".config/autostart")
AUTOSTART_SISTEMA = Path("/etc/xdg/autostart")

_REPO = Path(__file__).resolve().parents[2]
SKINS_MINTSKINS = [p for p in (Path("/usr/share/mintskins/skins"), _REPO / "skins") if p.is_dir()]
LOGIN_HELPER = next((p for p in (Path("/usr/lib/mintskins/mintskins-login-helper"),
                                 _REPO / "helpers/mintskins-login-helper") if p.exists()),
                    Path("/usr/lib/mintskins/mintskins-login-helper"))

# pastas de antes da troca do nome MintSkin -> MintSkins
PASTAS_ANTIGAS = [(Path(HOME, ".local/share/mintskin"), DADOS), (Path(HOME, ".config/mintskin"), CONFIG),
                  (Path(HOME, ".cache/mintskin"), CACHE),
                  (Path(HOME, ".local/share/fonts/mintskin"), Path(HOME, ".local/share/fonts/mintskins"))]


def migrar_pastas_antigas():
    for antiga, nova in PASTAS_ANTIGAS:
        if antiga.is_dir() and not antiga.is_symlink() and not nova.exists():
            nova.parent.mkdir(parents=True, exist_ok=True)
            antiga.rename(nova)


MAC_SH_BACKUP = Path(HOME, ".config/ativar_mac_automatico/backup")
MAC_SH_ATIVO = Path(HOME, ".config/ativar_mac_automatico/ativo")
