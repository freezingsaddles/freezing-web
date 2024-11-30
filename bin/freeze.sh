#!/usr/bin/env bash
#
# freeze.sh
#
# Overwrite freezing/meta.py with the current commit, branch name and build date.

# Set unofficial bash strict mode http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

# Thanks https://stackoverflow.com/a/64195658/424301
SHORT_SHA="$(echo "${GITHUB_SHA:-unknown}" | cut -c1-8)"
GITHUB_REF_NAME=${GITHUB_REF_NAME:-unknown}

cat <<EOF > "freezing/meta.py"
commit = "$SHORT_SHA"
branch = "$GITHUB_REF_NAME"
build_date = "$(date -u +'%Y%m%dT%H%M%SZ')"
EOF
