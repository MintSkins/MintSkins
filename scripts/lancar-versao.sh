#!/usr/bin/env bash
# Publica uma versao nova do MintSkins no GitHub. Quem tem o app instalado recebe o aviso.
#   ./scripts/lancar-versao.sh 1.1.0
set -euo pipefail
cd "$(dirname "$0")/.."

VERSAO=${1:?uso: $0 X.Y.Z}
[[ $VERSAO =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "versao invalida: $VERSAO"; exit 1; }
git diff --quiet || { echo "ha mudancas sem commit; faca o commit antes"; exit 1; }

sed -i "s/^__version__ = .*/__version__ = \"$VERSAO\"/" mintskins/__init__.py
./build-deb.sh
DEB="dist/mintskins_${VERSAO}_all.deb"


git commit -am "Versao $VERSAO"
git tag "v$VERSAO"
git push && git push origin "v$VERSAO"

if command -v gh >/dev/null; then
  gh release create "v$VERSAO" "$DEB" dist/SHA256SUMS --title "MintSkins $VERSAO" --generate-notes
else
  echo
  echo "Falta criar a Release no GitHub (sem o gh instalado):"
  echo "  https://github.com/PablUoo/MintSkins/releases/new?tag=v$VERSAO"
  echo "  anexe: $DEB e dist/SHA256SUMS"
fi
