import os
import sys

from .cli import main

if os.geteuid() == 0 and os.environ.get("MINTSKINS_PERMITIR_ROOT") != "sim":
    sys.exit("Nao rode o MintSkins como root: o visual seria aplicado no usuario root.")
sys.exit(main(sys.argv[1:]))
