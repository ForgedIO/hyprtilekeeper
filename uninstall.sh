#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
if [[ ${1:-} == --help ]]; then
  echo 'Usage: ./uninstall.sh [--offline]'
  echo 'Remove the installer-managed plugin and configuration. No sudo needed.'
  echo '--offline: remove files without contacting Hyprland (for a stopped/broken session).'
  exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --offline ) ]] || { echo 'Unknown option. Use --help.' >&2; exit 1; }
[[ $EUID != 0 ]] || { echo 'Run as your desktop user, without sudo.' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3 is required (installed by install.sh).' >&2; exit 1; }
exec python3 scripts/uninstall.py "$@"
