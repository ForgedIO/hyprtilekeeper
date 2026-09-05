"""Remove only installer-owned configuration and the installed shared library."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from install import BEGIN, END, atomic_write, run


def remove_block(text):
    if BEGIN not in text and END not in text:
        return text
    pattern = re.escape(BEGIN) + r'\n.*?^' + re.escape(END) + r'(?:\n|$)'
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise RuntimeError('Malformed installer block; no files changed.')
    cleaned, count = re.subn(pattern, '', text, flags=re.S | re.M)
    if count != 1:
        raise RuntimeError('Malformed installer block; no files changed.')
    return cleaned


def main():
    offline = '--offline' in sys.argv
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'hypr/hyprland.lua'
    plugin = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'hyprtilekeeper/hyprtilekeeper.so'
    original = config.read_text() if config.exists() else ''
    cleaned = remove_block(original)
    # Never remove a library still referenced by custom configuration.
    references = []
    for path in config.parent.rglob('*.lua'):
        if any(part.startswith('tilekeeper-backup-') or part.startswith('tilekeeper-uninstall-backup-') for part in path.parts):
            continue
        text = cleaned if path == config else path.read_text()
        if any(('hyprtilekeeper.so' in line or 'hl.plugin.tilekeeper' in line or re.search(r'layout\s*=\s*["\']tilekeeper["\']', line))
               and not line.lstrip().startswith('--') for line in text.splitlines()):
            references.append(str(path))
    if references:
        raise RuntimeError('Manual Tile Keeper configuration remains in: ' + ', '.join(references) + '. Remove those plugin load, shortcut, and tilekeeper layout settings first, then rerun. No files changed.')
    if cleaned == original and not plugin.exists():
        print('Nothing to uninstall: no managed configuration or installed library found.')
        return
    if not offline:
        if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
            raise RuntimeError('No Hyprland session selected. Use --offline from a TTY or stopped session.')
        # Hidden windows belong to the live plugin. PLUGIN_EXIT unhides them;
        # switch layouts before unloading so no layout instances reference its code.
        loaded = 'hyprtilekeeper' in run('hyprctl', 'plugin', 'list')
    else:
        loaded = False
    config.parent.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='tilekeeper-uninstall-backup-', dir=config.parent))
    if config.exists():
        shutil.copy2(config, backup / 'hyprland.lua')
    if plugin.exists():
        shutil.copy2(plugin, backup / 'hyprtilekeeper.so')
    print('Backup:', backup, flush=True)
    if loaded:
        run('hyprctl', 'eval', 'hl.config({general={layout="dwindle"}})')
        result = run('hyprctl', 'plugin', 'unload', str(plugin))
        if 'hyprtilekeeper' in run('hyprctl', 'plugin', 'list'):
            raise RuntimeError(f'Could not unload plugin: {result}. Files left unchanged; layout is now dwindle.')
    try:
        if cleaned != original:
            atomic_write(config, cleaned.encode(), config.stat().st_mode & 0o777)
        if not offline:
            run('hyprctl', 'reload')
            errors = run('hyprctl', 'configerrors')
            if errors:
                raise RuntimeError(errors)
        if plugin.exists():
            plugin.unlink()
        # Leave backups, package dependencies, source checkout, and unrelated files.
        if plugin.parent.is_dir() and not any(plugin.parent.iterdir()):
            plugin.parent.rmdir()
    except Exception as cause:
        if (backup / 'hyprtilekeeper.so').exists():
            plugin.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(plugin, (backup / 'hyprtilekeeper.so').read_bytes(), 0o755)
        if (backup / 'hyprland.lua').exists():
            atomic_write(config, (backup / 'hyprland.lua').read_bytes(), (backup / 'hyprland.lua').stat().st_mode & 0o777)
        if not offline:
            try:
                run('hyprctl', 'reload')
            except Exception:
                pass
        raise RuntimeError(f'Uninstall failed ({cause}); configuration restored from {backup}.') from cause
    print('Uninstalled Tile Keeper. Dependencies, source checkout, and backups were kept.')
    if offline:
        print('Start a new Hyprland session to apply this. Any existing process may still have the plugin loaded.')
    else:
        print('Default configuration bindings are active again. Switching layouts may rearrange tiles.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Uninstall stopped: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.output:
            print(error.output, file=sys.stderr)
        sys.exit(1)
