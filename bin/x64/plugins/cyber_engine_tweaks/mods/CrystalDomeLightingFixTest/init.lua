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

-- Measurement: for each stand-in on this car, is it on, is its panel on, and where does it
-- sit relative to its panel, in the car's own directions (mm): right, forward, up.
-- A left-side panel should show a negative "right", a right-side one positive, a windscreen
-- positive "forward"/"up": that is, outward. The log also goes to the CET log file.
local function dot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end

registerHotkey("cdlf_report_standins", "Report dome stand-ins", function()
    local player = Game.GetPlayer()
    local vehicle = player and Game.GetMountedVehicle(player)
    if not vehicle then
        print("[Crystal Dome Lighting Fix] Not in a vehicle.")
        return
    end
    local right, forward, up = vehicle:GetWorldRight(), vehicle:GetWorldForward(), vehicle:GetWorldUp()
    local found = 0
    local okName, carName = pcall(function() return vehicle:GetDisplayName() end)
    local okDome, dome = pcall(function() return vehicle:GetVehiclePS():GetCrystalDomeState() end)
    print("[Crystal Dome Lighting Fix] Report for " .. (okName and tostring(carName) or "?") ..
        ", dome on: " .. (okDome and tostring(dome) or "?"))
    for _, name in ipairs(names) do
        local standin = vehicle:FindComponentByName(CName.new(name))
        if standin then
            found = found + 1
            local panel = vehicle:FindComponentByName(CName.new(string.sub(name, 6)))
            local line = string.format("  %-28s stand-in %s", name, standin:IsEnabled() and "on " or "off")
            if panel then
                local a, b = standin:GetLocalToWorld().W, panel:GetLocalToWorld().W
                local d = { x = a.x - b.x, y = a.y - b.y, z = a.z - b.z }
                line = line .. string.format("  panel %s  offset right %+.1f forward %+.1f up %+.1f mm",
                    panel:IsEnabled() and "on " or "off", dot(d, right) * 1000, dot(d, forward) * 1000, dot(d, up) * 1000)
            else
                line = line .. "  panel not found"
            end
            print(line)
            spdlog.info(line)
        end
    end
    print(string.format("[Crystal Dome Lighting Fix] %d stand-ins on this car.", found))
end)
