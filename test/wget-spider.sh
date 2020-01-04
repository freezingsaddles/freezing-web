#!/usr/bin/env bash
#
# wget-spider.sh
#
# Uses wget to spider all the assets of a web site

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

TMPFILE=$(mktemp -t wget-spider.XXXXXX)
# http://redsymbol.net/articles/bash-exit-traps/ 
function finish {
  rm -f "$TMPFILE"
}
trap finish EXIT

OUTFILE=${OUTFILE:-$TMPFILE}
URL=${URL:-http://localhost:5000}

if ! time wget -r -nd --delete-after "$URL" > "$OUTFILE" 2>&1; then
    RETCODE=$?
    cat <<EOF
ERROR: wget spider returned non-zero exit code $RETCODE
ERROR: entire output of wget follows:

EOF
    cat "$OUTFILE"
    cat <<EOT

ERROR: examine output carefully for error and failure non-'200 OK' responses:

EOT
    (grep -E -i ^--\|HTTP\|failed\|error \
        | grep -v 200 \
        | grep -E -i -B 1 HTTP\|failed\|error) \
        < "$OUTFILE"
    exit $RETCODE
fi
