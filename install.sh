#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
if [[ ${1:-} == --help ]]; then
  echo 'Usage: ./install.sh [--check]'
  echo 'Install on Arch/Omarchy; --check checks prerequisites without changing anything.'
  exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --check ) ]] || { echo 'Unknown option. Use --help.' >&2; exit 1; }
[[ $EUID != 0 ]] || { echo 'Run as your desktop user, without sudo. Only package installation needs elevation.' >&2; exit 1; }
source /etc/os-release
[[ ${ID:-} == arch || ${ID:-} == omarchy || " ${ID_LIKE:-} " == *' arch '* ]] || {
  echo 'Automatic installation currently supports Arch Linux and Omarchy only.' >&2; exit 1;
}
missing=()
for package in gcc pkgconf lua python hyprland; do
  pacman -Q "$package" >/dev/null 2>&1 || missing+=("$package")
done
if ((${#missing[@]})); then
  echo "Required packages: ${missing[*]}"
  [[ ${1:-} != --check ]] || exit 1
  echo 'Missing system packages require administrator access (sudo). The plugin itself installs as your user.'
  if command -v omarchy >/dev/null; then
    omarchy pkg add "${missing[@]}"
  else
    sudo pacman -S --needed "${missing[@]}"
  fi
fi
exec python3 scripts/install.py "$@"
