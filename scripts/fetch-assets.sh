#!/bin/bash
# Fetch only the external synthesiser ROMs; original game files are supplied separately.
set -u
usage() { echo "Usage: $0 [destination]"; echo 'Fetch CM-32L, SC-55 and SCC-1A ROMs (default: roms in the project/package directory).'; }
if [[ "${1:-}" == --help ]]; then usage; exit 0; fi
if (( $# > 1 )); then usage >&2; exit 2; fi
script_dir=$(cd -- "$(dirname -- "$0")" && pwd) || exit 1
destination=${1:-$script_dir/../roms}
if [[ ! -r "$script_dir/roms.txt" ]]; then echo "ERROR: missing ROM manifest: $script_dir/roms.txt" >&2; exit 1; fi
for dependency in curl unzip; do
  if ! command -v "$dependency" >/dev/null; then echo "ERROR: install $dependency to fetch ROMs." >&2; exit 1; fi
done
if command -v sha256sum >/dev/null; then hash_command=(sha256sum);
elif command -v shasum >/dev/null; then hash_command=(shasum -a 256);
else echo 'ERROR: install sha256sum or shasum to verify ROMs.' >&2; exit 1; fi
mkdir -p -- "$destination" || exit 1
cd -- "$destination" || exit 1
temporary=$(mktemp -d .fetch-assets.XXXXXXXX) || exit 1
trap 'rm -rf -- "$temporary"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

matches() {
  [[ -f "$1" ]] || return 1
  local digest
  digest=$("${hash_command[@]}" -- "$1") || return 1
  [[ "${digest%% *}" == "$expected" ]]
}
download() {
  curl --user-agent 'Lost Engines TFX CPP' --fail --location \
    --retry 3 --retry-all-errors --retry-delay 2 --connect-timeout 30 \
    --output "$2" "$1"
}
archive_url=''
archive_ready=0
fetch() {
  if matches "$file"; then echo "$file: OK"; return 0; fi
  if [[ -d "$file" ]]; then echo "ERROR: $file is a directory." >&2; return 1; fi
  echo "Fetching $file"
  if [[ "$member" == - ]]; then
    download "$url" "$temporary/rom.tmp" || return 1
  else
    # Cache this archive once for its five SCC-1A members, including a failed
    # attempt. Extract just the named ROM, never the unrelated archive contents.
    if [[ "$archive_url" != "$url" ]]; then
      archive_url=$url
      archive_ready=0
      if download "$url" "$temporary/archive.zip"; then archive_ready=1; fi
    fi
    (( archive_ready )) || return 1
    unzip -p "$temporary/archive.zip" "$member" > "$temporary/rom.tmp" || return 1
  fi
  if ! matches "$temporary/rom.tmp"; then echo "ERROR: $file failed SHA-256 verification." >&2; return 1; fi
  mv -f -- "$temporary/rom.tmp" "$file"
}
failed=0
while read -r expected file url member; do
  [[ -z "$expected" || "$expected" == \#* ]] && continue
  member=${member%$'\r'}
  if ! fetch; then echo "ERROR: could not fetch a verified $file. Rerun this script to retry." >&2; failed=1; fi
done < "$script_dir/roms.txt"
if (( failed )); then exit 1; fi
echo "ROMs ready in $PWD"
echo 'Use --rom-dir with this directory to enable Roland music.'
