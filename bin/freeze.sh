#!/usr/bin/env sh
set -eu
TMPFILE=$(mktemp tmp.freeze.XXXXXX)
python3 <<EOF > "$TMPFILE"
from freezing.meta import freeze
print(freeze())
EOF
mv "$TMPFILE" freezing/meta.py
rm -f "$TMPFILE"
