#!/usr/bin/env bash
# Publica uma versao nova do MintSkins no GitHub. Quem tem o app instalado recebe o aviso.
#   ./scripts/lancar-versao.sh 1.1.0
# As notas da release sao os commits desde a versao anterior (escreva commits que digam o que mudou).
set -euo pipefail
cd "$(dirname "$0")/.."

VERSAO=${1:?uso: $0 X.Y.Z}
[[ $VERSAO =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "versao invalida: $VERSAO"; exit 1; }
git diff --quiet || { echo "ha mudancas sem commit; faca o commit antes"; exit 1; }

ANTERIOR=$(git describe --tags --abbrev=0 2>/dev/null || true)
NOTAS=$(git log --no-merges --pretty='- %s' ${ANTERIOR:+"$ANTERIOR"..HEAD} | grep -v '^- Versao ' || true)
[ -n "$NOTAS" ] || { echo "nenhum commit desde $ANTERIOR: nada para lancar"; exit 1; }
[ -n "$ANTERIOR" ] && NOTAS="$NOTAS

**Full Changelog**: https://github.com/MintSkins/MintSkins/compare/$ANTERIOR...v$VERSAO"

sed -i "s/^__version__ = .*/__version__ = \"$VERSAO\"/" mintskins/__init__.py
./build-deb.sh
DEB="dist/mintskins_${VERSAO}_all.deb"


git commit -am "Versao $VERSAO"
git tag "v$VERSAO"
git push && git push origin "v$VERSAO"

if command -v gh >/dev/null; then
  gh release create "v$VERSAO" "$DEB" dist/SHA256SUMS --title "MintSkins $VERSAO" --notes "$NOTAS"
else
  echo
  echo "Falta criar a Release no GitHub (sem o gh instalado):"
  echo "  https://github.com/MintSkins/MintSkins/releases/new?tag=v$VERSAO"
  echo "  anexe: $DEB e dist/SHA256SUMS"
  echo "  notas:"; echo "$NOTAS"
fi
