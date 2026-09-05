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

## Build and configure

Requirements: C++23 compiler, GNU Make, pkg-config, and matching Hyprland
headers with their dependencies. Build from the repository directory:

```sh
git clone https://github.com/ForgedIO/hyprtilekeeper.git
cd hyprtilekeeper
make
```

Add this after default settings that choose your layout, replacing the path:

```lua
hl.plugin.load("/absolute/path/to/hyprtilekeeper/hyprtilekeeper.so")
hl.config({
    general = { layout = "tilekeeper" },
    dwindle = { preserve_split = true },
})

-- Replaces any existing actions on these shortcuts.
hl.unbind("SUPER + M")
hl.unbind("SUPER + CTRL + M")
hl.bind("SUPER + M", function() hl.plugin.tilekeeper.minimize() end)
hl.bind("SUPER + CTRL + M", function() hl.plugin.tilekeeper.restore() end)
```

On Omarchy, put the plugin load and layout settings after the defaults in
`~/.config/hypr/hyprland.lua`, and shortcuts in `~/.config/hypr/bindings.lua`.

```sh
hyprctl reload
hyprctl configerrors
```

A `hyprpm.toml` manifest is included. Manual loading as shown above is the
installation method tested so far. Use one loading method at a time.

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

Restore hidden tiles first, then switch to dwindle before unloading:

```sh
hyprctl eval 'hl.config({general={layout="dwindle"}})'
hyprctl plugin unload /absolute/path/to/hyprtilekeeper/hyprtilekeeper.so
```

To remove, delete the plugin load and shortcuts from your configuration and
configure `dwindle` as your layout. To update, rebuild and load the plugin,
then select `tilekeeper` again. Switching layouts can rearrange tiles.
Build output is replaced atomically to avoid overwriting a loaded library.

## Testing

Tests require Python 3, `foot`, and a disposable nested Hyprland session with
access to the parent Wayland display. From the repository directory:

```sh
TILEKEEPER_PLUGIN="$PWD/hyprtilekeeper.so" Hyprland --config "$PWD/tests/nested.lua"
```

In another terminal, use `hyprctl instances` to find the nested instance:

```sh
python3 tests/integration.py NESTED_INSTANCE_SIGNATURE
```

The test closes a disposable terminal. Do not target your regular desktop.
Verified on 0.56.2: each tile's exact geometry, hide-all/reverse-order restore,
unequal splits, and closing a hidden tile. This does not establish safety for
every layout action.

## Reporting problems

Include `hyprctl version`, plugin version, relevant layout settings, and steps
to reproduce. Mention grouping, fullscreen, workspace moves, and monitor changes.
Review logs for private window titles before sharing.

## License

[GNU General Public License v3.0](LICENSE) (GPL-3.0-only).
