#!/usr/bin/env bash
#
# wget-spider.sh
#
# Uses wget to spider all the assets of a web site, as the simplest possible functional test. If any resources come back with 500 errors, wget will exit with a non-zero error code, and this will print the output of wget and try to highlight errors.
#
# MIT Licensed
#
# Copyright 2020 Richard Bullington-McGuire
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
