"""User-level installer; only install.sh's package step requires root."""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
BEGIN = '-- BEGIN hyprtilekeeper installer'
END = '-- END hyprtilekeeper installer'


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def managed_config(original, plugin):
    if original.count(BEGIN) != original.count(END) or original.count(BEGIN) > 1:
        raise RuntimeError('Malformed installer block; configuration was not changed.')
    original = re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '', original, flags=re.S)
    # Migrate the documented, single-line manual load. Leave all other user code intact.
    original = re.sub(r'^\s*hl\.plugin\.load\(["\'][^"\'\n]*hyprtilekeeper\.so["\']\)\s*$', '', original, flags=re.M)
    block = f'''{BEGIN}
hl.plugin.load({json.dumps(str(plugin))})
hl.config({{general = {{layout = "tilekeeper"}}, dwindle = {{preserve_split = true}}}})
hl.unbind("SUPER + M")
hl.unbind("SUPER + CTRL + M")
hl.bind("SUPER + M", function() hl.plugin.tilekeeper.minimize() end)
hl.bind("SUPER + CTRL + M", function() hl.plugin.tilekeeper.restore() end)
{END}
'''
    return original.rstrip() + '\n\n' + block


def atomic_write(path, data, mode=0o644):
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    check = '--check' in sys.argv
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'hypr/hyprland.lua'
    if not config.is_file():
        raise RuntimeError(f'Expected Lua configuration at {config}. Legacy .conf configurations are unsupported.')
    for tool in ('g++', 'pkg-config', 'hyprctl'):
        if not shutil.which(tool):
            raise RuntimeError(f'Missing {tool}; rerun ./install.sh to install dependencies.')
    flags = shlex.split(run('pkg-config', '--cflags', 'hyprland'))
    macros = run('g++', '-dM', '-E', '-x', 'c++', *flags, '-include', 'hyprland/src/version.h', '/dev/null')
    header = re.search(r'^#define GIT_COMMIT_HASH "([^"]+)"', macros, re.M)
    tag = re.search(r'^#define GIT_TAG "([^"]+)"', macros, re.M)
    if not tag or tag[1] != 'v0.56.2':
        raise RuntimeError('This release supports Hyprland 0.56.2 only. No configuration was changed.')
    version = json.loads(run('hyprctl', '-j', 'version'))
    if not header or version.get('commit') != header[1]:
        raise RuntimeError('Running Hyprland and installed headers differ. Log out and back in after your system update, then retry.')
    errors = run('hyprctl', 'configerrors')
    if errors:
        raise RuntimeError('Fix existing Hyprland configuration errors first:\n' + errors)
    destination = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'hyprtilekeeper/hyprtilekeeper.so'
    original = config.read_text()
    configured = managed_config(original, destination)
    loaded = 'hyprtilekeeper' in run('hyprctl', 'plugin', 'list')
    if loaded and BEGIN not in original:
        raise RuntimeError('A manually installed tilekeeper is loaded. Restore hidden tiles, switch to dwindle, and unload that plugin before installing. See README migration instructions.')
    bindings = json.loads(run('hyprctl', '-j', 'binds'))
    for bind in bindings:
        if str(bind.get('key', '')).upper() == 'M' and bind.get('modmask') in (64, 68):
            print('Replacing shortcut:', bind.get('description') or bind.get('dispatcher'), bind.get('arg', ''))
    # Omarchy's workspace-layout-toggle saves per-workspace layout overrides
    # (e.g. dwindle) that silently override the global layout.  Clear them so
    # every workspace uses the tilekeeper layout.
    state_home = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local' / 'state')))
    layouts_dir = state_home / 'omarchy' / 'workspace-layouts'
    if layouts_dir.is_dir():
        removed = []
        for lua_file in sorted(layouts_dir.glob('*.lua')):
            removed.append(lua_file.name)
            lua_file.unlink()
        if removed:
            print('Cleared saved workspace layout overrides:', ', '.join(removed))
    print('Compatibility checks passed. Plugin destination:', destination)
    if check:
        print('Check only: no files or packages changed.')
        return
    print('Building plugin…')
    with tempfile.TemporaryDirectory(prefix='tilekeeper-build-') as temporary:
        built = Path(temporary) / 'hyprtilekeeper.so'
        subprocess.run(['g++', '-std=c++23', '-O2', '-fPIC', '-shared', '-Wall', '-Wextra',
                        *flags, '-o', str(built), str(ROOT / 'src/main.cpp')], check=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = Path(tempfile.mkdtemp(prefix='tilekeeper-backup-', dir=config.parent))
        shutil.copy2(config, backup / 'hyprland.lua')
        previous = destination.read_bytes() if destination.exists() else None
        if previous is not None:
            (backup / 'hyprtilekeeper.so').write_bytes(previous)
        print('Backup:', backup)
        try:
            atomic_write(destination, built.read_bytes(), 0o755)
            atomic_write(config, configured.encode(), config.stat().st_mode & 0o777)
            run('hyprctl', 'reload')
            errors = run('hyprctl', 'configerrors')
            if errors:
                raise RuntimeError(errors)
            run('hyprctl', 'eval', 'assert(hl.plugin.tilekeeper and hl.plugin.tilekeeper.minimize and hl.plugin.tilekeeper.restore)')
        except Exception as cause:
            atomic_write(config, (backup / 'hyprland.lua').read_bytes(), (backup / 'hyprland.lua').stat().st_mode & 0o777)
            if previous is not None:
                atomic_write(destination, previous, 0o755)
            # Keep a newly loaded library on disk; never unload in-process code during recovery.
            try:
                run('hyprctl', 'reload')
                print('Configuration restored. Remaining errors:', run('hyprctl', 'configerrors'))
            except Exception as error:
                print('Could not reload restored config:', error)
            raise RuntimeError(f'Installation failed ({cause}); configuration restored from {backup}. Any newly loaded plugin remains loaded until logout.')
    print('Installed. Super + M hides a tile; Super + Ctrl + M restores it.')
    if loaded:
        print('An existing build remains active. Restore hidden tiles, then log out and back in to use the new build.')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f'Installation stopped: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.output:
            print(error.output, file=sys.stderr)
        sys.exit(1)
