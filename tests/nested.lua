hl.monitor({ output = "", mode = "1280x720@60", position = "0x0", scale = 1 })
hl.plugin.load(assert(os.getenv("TILEKEEPER_PLUGIN"), "Set TILEKEEPER_PLUGIN to the absolute path of hyprtilekeeper.so"))
hl.config({
    general = {
        layout = "tilekeeper",
        gaps_in = 6,
        gaps_out = 10,
    },
    dwindle = {
        preserve_split = true,
    },
})
hl.bind("SUPER + M", function() hl.plugin.tilekeeper.minimize() end)
hl.bind("SUPER + CTRL + M", function() hl.plugin.tilekeeper.restore() end)
hl.on("hyprland.start", function()
    hl.exec_cmd("foot --title keeper-one")
    hl.exec_cmd("foot --title keeper-two")
    hl.exec_cmd("foot --title keeper-three")
end)
