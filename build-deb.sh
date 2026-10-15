#!/usr/bin/env bash
# Gera dist/mintskins_<versao>_all.deb e dist/SHA256SUMS
set -euo pipefail
umask 022
cd "$(dirname "$0")"

PACOTE=mintskins
VERSAO=$(python3 -c 'import mintskins; print(mintskins.__version__)')
MANTENEDOR=${MANTENEDOR:-"MintSkins <PablUoo@users.noreply.github.com>"}
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct 2>/dev/null || date +%s)}
SAIDA="dist/${PACOTE}_${VERSAO}_all.deb"

RAIZ=$(mktemp -d)
trap 'rm -rf "$RAIZ"' EXIT
chmod 755 "$RAIZ"

passo() { printf '\n== %s\n' "$*"; }
falha() { echo "ERRO: $*" >&2; exit 1; }

passo "MintSkins $VERSAO"
if [ -d tests ]; then
  python3 -m unittest discover -s tests -q 2>/dev/null || falha "testes falharam"
fi
desktop-file-validate data/io.github.pabluoo.MintSkins.desktop || falha ".desktop invalido"
if command -v appstreamcli >/dev/null; then
  appstreamcli validate --no-net data/io.github.pabluoo.MintSkins.metainfo.xml >/dev/null || falha "metainfo invalido"
fi
sh -n empacotamento/postinst && sh -n empacotamento/prerm && sh -n helpers/mintskins-login-helper

passo "Arquivos"
DOC="$RAIZ/usr/share/doc/$PACOTE"
install -d "$RAIZ/DEBIAN" "$DOC" "$RAIZ/usr/share/mintskins/skins" "$RAIZ/usr/share/man/man1"
(cd mintskins && find . -type f \( -name '*.py' -o -name '*.css' -o -name '*.svg' -o -name '*.ttf' -o -name 'OFL-*.txt' \) -not -path '*/__pycache__/*' \
  -exec install -D -m 644 {} "$RAIZ/usr/lib/mintskins/mintskins/{}" \;)
install -D -m 755 bin/mintskins "$RAIZ/usr/bin/mintskins"
ln -s mintskins "$RAIZ/usr/bin/mintskin"   # nome antigo, para quem ja usava o comando
install -D -m 755 helpers/mintskins-login-helper "$RAIZ/usr/lib/mintskins/mintskins-login-helper"
install -D -m 644 data/io.github.pabluoo.MintSkins.desktop "$RAIZ/usr/share/applications/io.github.pabluoo.MintSkins.desktop"
install -D -m 644 data/io.github.pabluoo.MintSkins.metainfo.xml "$RAIZ/usr/share/metainfo/io.github.pabluoo.MintSkins.metainfo.xml"
install -D -m 644 data/polkit/io.github.pabluoo.mintskins.policy "$RAIZ/usr/share/polkit-1/actions/io.github.pabluoo.mintskins.policy"
install -D -m 644 data/mintskins-mime.xml "$RAIZ/usr/share/mime/packages/mintskins.xml"
cp -a skins/. "$RAIZ/usr/share/mintskins/skins/"
find "$RAIZ/usr/share/mintskins" -type d -exec chmod 755 {} +
find "$RAIZ/usr/share/mintskins" -type f -exec chmod 644 {} +

passo "Icones"
install -D -m 644 data/icons/mintskins.svg "$RAIZ/usr/share/icons/hicolor/scalable/apps/mintskins.svg"
python3 - "$RAIZ/usr/share/icons/hicolor" <<'PY'
import sys
from pathlib import Path
import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf
for t in (16, 24, 32, 48, 64, 128, 256, 512):
    destino = Path(sys.argv[1], f"{t}x{t}", "apps", "mintskins.png")
    destino.parent.mkdir(parents=True, exist_ok=True)
    GdkPixbuf.Pixbuf.new_from_file_at_scale("data/icons/mintskins.svg", t, t, True).savev(str(destino), "png", [], [])
    destino.chmod(0o644)
PY

passo "Documentacao"
install -m 644 README.md "$DOC/README.md"
install -m 644 empacotamento/copyright "$DOC/copyright"
gzip -9n -c empacotamento/changelog > "$DOC/changelog.gz"
sed "s/@VERSAO@/$VERSAO/" empacotamento/mintskins.1 | gzip -9n > "$RAIZ/usr/share/man/man1/mintskins.1.gz"
chmod 644 "$DOC/changelog.gz" "$RAIZ/usr/share/man/man1/mintskins.1.gz"

passo "Controle"
install -m 755 empacotamento/postinst empacotamento/prerm "$RAIZ/DEBIAN/"
TAMANHO=$(python3 - "$RAIZ" <<'PY'
import os, sys
total = 0
for raiz, dirs, arqs in os.walk(sys.argv[1]):
    dirs[:] = [d for d in dirs if d != "DEBIAN"]
    for n in dirs + arqs:
        p = os.path.join(raiz, n)
        total += 1 if os.path.islink(p) or os.path.isdir(p) else -(-os.path.getsize(p) // 1024)
print(total)
PY
)
sed -e "s/@VERSAO@/$VERSAO/" -e "s/@TAMANHO@/$TAMANHO/" -e "s/@MANTENEDOR@/$MANTENEDOR/" \
  empacotamento/control > "$RAIZ/DEBIAN/control"
(cd "$RAIZ" && find usr -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum > DEBIAN/md5sums)
chmod 644 "$RAIZ/DEBIAN/control" "$RAIZ/DEBIAN/md5sums"

passo "Pacote"
find "$RAIZ" -type d -exec chmod 755 {} +
find "$RAIZ" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
mkdir -p dist
dpkg-deb --root-owner-group -Zxz --build "$RAIZ" "$SAIDA" >/dev/null
(cd dist && sha256sum "$(basename "$SAIDA")" > SHA256SUMS)

dpkg-deb --field "$SAIDA" Package Version Architecture Installed-Size
echo "pronto: $SAIDA ($(du -h "$SAIDA" | cut -f1))"
echo "instalar: sudo apt install ./$SAIDA"
