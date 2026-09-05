# Changelog

## Unreleased

- Add `./install.sh` for dependency installation, compilation, backed-up Lua
  configuration, and validation on Arch/Omarchy.
- Add a read-only prerequisite check and installer rollback tests.
- Document when dependency installation requires sudo.

## 0.2.0

Initial public candidate, tested on Hyprland 0.56.2 and Omarchy 4.0.2.

- Hide and restore tiles while retaining their dwindle-tree placement.
- Restore multiple hidden tiles in reverse order on the active workspace.
- Native Lua functions for shortcuts and scripting.
- Reject floating, grouped, fullscreen windows and mismatched builds.
- Atomic build output replacement.
- Integration checks for exact geometry, hide-all, unequal splits, and closing
  a hidden tile.
