#!/bin/sh
# usage: fetch.sh <lab_id> <url> [filename]
# Downloads one public source into ../_raw/ranges/<lab_id>/ (next to this repository) and appends a line to ../_raw/ranges/fetch_log.tsv
set -eu
RAW="$(cd "$(dirname "$0")/../.." && pwd)/_raw/ranges"
lab="$1"; url="$2"; name="${3:-$(basename "${url%%\?*}" | sed 's/%20/_/g')}"
mkdir -p "$RAW/$lab"
out="$RAW/$lab/$name"
code=$(curl -sSL -m 90 -A 'Mozilla/5.0 (compatible; reference-interval research snapshot)' -o "$out" -w '%{http_code}' "$url")
sha=$(shasum -a 256 "$out" | cut -d' ' -f1)
printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$lab" "$url" "$lab/$name" "$code" "$sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$RAW/fetch_log.tsv"
chmod 444 "$out"; echo "$code $sha $out $(wc -c < "$out")"
