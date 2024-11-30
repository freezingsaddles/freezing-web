#!/usr/bin/env sh
python3 <<EOF > freezing/web/utils/meta.py
from freezing.web.utils.meta import freeze
print(freeze())
EOF
