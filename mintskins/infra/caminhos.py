"""Onde o MintSkins le e grava as coisas."""
import subprocess
from pathlib import Path

HOME = str(Path.home())
DADOS = Path(HOME, ".local/share/mintskins")
SKINS_USUARIO = DADOS / "skins"
INSTALADOS = DADOS / "instalados"
DESFAZER = DADOS / "desfazer"
NUVEM_LOCAL = DADOS / "nuvem"
CONFIG = Path(HOME, ".config/mintskins")
CACHE = Path(HOME, ".cache/mintskins")
PASTA_FONTES = Path(HOME, ".local/share/fonts/mintskins")

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
                  (Path(HOME, ".local/share/fonts/mintskin"), PASTA_FONTES)]


def migrar_pastas_antigas():
    """Move a pasta antiga para o nome novo, uma vez so. Fica um atalho no lugar da antiga: assim, se
    a pessoa apagar a pasta nova depois, a antiga nao volta (antes ela "ressuscitava" skins apagadas)."""
    for antiga, nova in PASTAS_ANTIGAS:
        if not antiga.is_dir() or antiga.is_symlink():
            continue
        try:
            if nova.exists():   # as duas existem: a antiga ficou parada; tira do caminho sem apagar nada
                antiga.rename(antiga.with_name(antiga.name + ".antiga"))
                continue
            nova.parent.mkdir(parents=True, exist_ok=True)
            antiga.rename(nova)
            antiga.symlink_to(nova)
            if nova == PASTA_FONTES:
                atualizar_cache_de_fontes()
        except OSError:
            pass


def atualizar_cache_de_fontes():
    """Refaz o cache do fontconfig da pasta de fontes do MintSkins. O fontconfig so confere a data da
    pasta: depois de renomear ou trocar arquivos o cache velho continua "valido", e apps Chromium/Electron
    (FortiClient, por exemplo) leem a fonte errada e abrem com a janela em branco."""
    if PASTA_FONTES.is_dir():
        subprocess.run(["fc-cache", "-f", str(PASTA_FONTES)], capture_output=True)


MAC_SH_BACKUP = Path(HOME, ".config/ativar_mac_automatico/backup")
MAC_SH_ATIVO = Path(HOME, ".config/ativar_mac_automatico/ativo")
