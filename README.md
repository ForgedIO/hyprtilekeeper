# hyprtilekeeper

Temporarily make room in your tiled workspace, then put the hidden window back
where it belongs.

**Super + M** hides the focused tile and lets the remaining tiles expand.
**Super + Ctrl + M** restores the most recently hidden tile on that workspace.
The window keeps its place in the dwindle tree, including its parent, side, and
split ratio.

Hide a reference window while doing quick work in your editor and terminal.
When you need the reference again, restore it with one shortcut.

## Status

Experimental **v0.2.0**, tested on **Hyprland 0.56.2** with Lua configuration
on Omarchy 4.0.2. Omarchy is not required. Other Hyprland versions are untested.
The plugin uses private dwindle internals and requires matching Hyprland headers
and ABI. It rejects mismatched builds. See the official
[plugin documentation](https://wiki.hypr.land/Plugins/Using-Plugins/).

## Install

On **Omarchy or Arch Linux running Hyprland 0.56.2 with Lua configuration**:

```sh
git clone https://github.com/ForgedIO/hyprtilekeeper.git
cd hyprtilekeeper
./install.sh
```

You can also download and extract this repository from GitHub, open a terminal
in the extracted directory, and run `./install.sh`. No Git or Make commands are
needed with that method.

**Run as your normal desktop user, without sudo.** The plugin installs into
`~/.local/share/hyprtilekeeper/`, and only your user configuration is edited.
If dependencies are already installed, no sudo is used. If packages are missing,
the installer lists them and uses the system package manager, which requires
**sudo for that package installation step only** and may ask for your password.
Never run `sudo ./install.sh`.

The installer:

1. Installs missing compiler, pkg-config, Lua, Python, and Hyprland packages.
2. Checks the supported Hyprland version and running compositor/header match.
3. Builds the plugin automatically, without requiring you to run `make`.
4. Backs up your Lua configuration and any previously installed plugin.
5. Adds the plugin, layout settings, and both shortcuts to `hyprland.lua`.
6. Reloads and checks configuration, restoring the backup if validation fails.

Super + M and Super + Ctrl + M replace any existing actions on those keys.
The installer prints their previous bindings. Selecting the tilekeeper layout
can rearrange existing windows.

A running Hyprland session and an existing `~/.config/hypr/hyprland.lua` are
required. XDG_CONFIG_HOME and XDG_DATA_HOME are respected. Other distributions
and legacy `.conf` configurations are not supported by the automatic installer.
Dependencies are installed from your configured repositories; this script does
not perform a full system upgrade or downgrade Hyprland to an older version.
If installed headers differ from the running session, it stops and asks you to
log out and back in after your system update.

Check prerequisites without changing files or installing packages:

```sh
./install.sh --check
```

Configuration backups are saved as `tilekeeper-backup-*` directories beside
`hyprland.lua`. Re-running the installer replaces its own configuration block
without duplicating it. For an existing manual installation, restore hidden tiles and unload the old
plugin before running the installer:

```sh
hyprctl eval 'hl.config({general={layout="dwindle"}})'
hyprctl plugin unload /absolute/path/to/old/hyprtilekeeper.so
```

The documented single-line manual load is then migrated. Custom plugin-manager
setups should use one installation method at a time.

For developers, `make` and `hyprpm.toml` remain available. They are not needed
for the standard installation above.

## Behavior and limits

- Hidden windows continue running on their original workspace.
- Restore works on the active workspace, most recently hidden first.
- Multiple tiles can be hidden, including every tile on a workspace.
- Floating, grouped, and fullscreen windows are rejected.
- Exact coordinates return when the surrounding tree and monitor geometry are
  unchanged. Adding, closing, moving, or resizing surrounding windows changes
  the available layout; restoring does not undo those changes.
- State lasts for the current session. Restore hidden tiles before switching
  layouts or updating. Monitor changes, grouping while tiles are hidden, and
  moving hidden windows through external tools have not been validated.

For scripts:

```sh
hyprctl eval 'hl.plugin.tilekeeper.minimize()'
hyprctl eval 'hl.plugin.tilekeeper.restore()'
```

Lua functions return a boolean and show a notification on failure. Legacy
`tilekeeper:minimize` and `tilekeeper:restore` dispatchers are also registered,
but `hyprctl dispatch tilekeeper:minimize` is invalid with the Lua parser.

## Updating or removing

For a Git clone, update and rerun the installer:

```sh
git pull --ff-only
./install.sh
```

An already loaded plugin remains active until the next login. Restore hidden
tiles, then log out and back in to activate the new build. The installer avoids
unloading code from your running compositor. If you downloaded a ZIP, download
the updated source and run its installer instead.

To remove, restore hidden tiles first. Delete the block between
`-- BEGIN hyprtilekeeper installer` and `-- END hyprtilekeeper installer` in
`hyprland.lua`, and set your layout to `dwindle` if it was manually configured
elsewhere. Log out and back in. You can then delete
`~/.local/share/hyprtilekeeper/`. If migrating from an older manual setup, also
remove its tilekeeper shortcuts and layout setting. Switching layouts can
rearrange tiles.

## Testing

Tests require Python 3, `foot`, and a disposable nested Hyprland session with
access to the parent Wayland display. From the repository directory:

```sh
TILEKEEPER_PLUGIN="${XDG_DATA_HOME:-$HOME/.local/share}/hyprtilekeeper/hyprtilekeeper.so" Hyprland --config "$PWD/tests/nested.lua"
```

In another terminal, use `hyprctl instances` to find the nested instance:

```sh
python3 tests/integration.py NESTED_INSTANCE_SIGNATURE
```

The test closes a disposable terminal. Do not target your regular desktop.
Verified on 0.56.2: each tile's exact geometry, hide-all/reverse-order restore,
unequal splits, and closing a hidden tile. This does not establish safety for
every layout action.

Installer checks can be run without touching a desktop:

```sh
python3 -m unittest discover -s tests -p test_installer.py
```

These use temporary directories and simulated compositor/package responses to
check configuration migration, repeat installation, backups, rollback, and
version mismatch rejection. `./install.sh --check` checks the real environment.

## Reporting problems

Include `hyprctl version`, plugin version, relevant layout settings, and steps
to reproduce. Mention grouping, fullscreen, workspace moves, and monitor changes.
Review logs for private window titles before sharing.

## License

[GNU General Public License v3.0](LICENSE) (GPL-3.0-only).
