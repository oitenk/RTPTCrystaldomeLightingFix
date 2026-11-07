-- Crystal Dome Lighting Fix: test hotkey (test builds only, not shipped).
-- Bind "Toggle dome stand-ins" in CET's Bindings tab. Each press flips the opaque
-- stand-ins behind the dark dome panels of the car you are sitting in, so the cabin
-- can be compared with and without them. Turning the dome on or off resets them.

local names = require("names")   -- names.lua, written by tools/build_archive.py

registerHotkey("cdlf_toggle_standins", "Toggle dome stand-ins", function()
    local player = Game.GetPlayer()
    local vehicle = player and Game.GetMountedVehicle(player)
    if not vehicle then
        print("[Crystal Dome Lighting Fix] Not in a vehicle.")
        return
    end
    local found, show = 0, nil
    for _, name in ipairs(names) do
        local component = vehicle:FindComponentByName(CName.new(name))
        if component then
            if show == nil then show = not component:IsEnabled() end
            component:Toggle(show)
            found = found + 1
        end
    end
    if found == 0 then
        print("[Crystal Dome Lighting Fix] No stand-ins on this car.")
    else
        print(string.format("[Crystal Dome Lighting Fix] Stand-ins %s (%d panels).", show and "ON" or "OFF", found))
    end
end)
