# Discord tester invitation draft

I've been working on **hyprtilekeeper**, a small Hyprland plugin for temporarily
reclaiming one tile's space while keeping the rest of your workspace tiled.

Example: I have an editor, terminal, and browser open. I want more room for the
terminal while still seeing the editor. **Super + M** hides the browser and lets
the remaining tiles expand. **Super + Ctrl + M** brings it back to its original
position and size, provided I haven't rearranged the surrounding layout.

**Super + F** is useful when I want one window fullscreen. This is for when I
still need two or more windows visible together, and just want one tile out of
the way for a few minutes.

Looking for testers on **Omarchy / Hyprland 0.56.2 with Lua config**. It's
experimental, supports ordinary dwindle tiles, and includes an `install.sh`
that handles dependencies, building, and configuration backups. Sudo is only
needed if system dependencies are missing. Floating, grouped, and fullscreen
windows aren't supported.

Try hiding/restoring a tile, hiding several, and using it in your normal
workflow. I'd appreciate reproduction steps for misplaced tiles, focus issues,
or crashes, along with your Hyprland version.

https://github.com/ForgedIO/hyprtilekeeper

---

Suggested attachment: a short recording of three tiles → hide one → work with
the remaining two visible → restore the original arrangement. Use disposable
windows without personal information. Keep the shortcuts visible in captions.
Three screenshots of those states are a useful alternative.
