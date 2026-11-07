# Crystal Dome Lighting Fix

A Cyberpunk 2077 mod for cars with a Crystal Dome. With the dome off, the panels around the cabin look solid, but with ray-traced reflections the cabin still picks up the bright world outside, as if the panels were clear glass. This mod puts a plain, opaque surface just outside each dark panel while the dome is off, so reflections stop there. When you turn the dome on, the surfaces disappear and the see-through look is as before.

**Status: test build.** Tested in the Militech Hellhound; the other cars are built the same way but not yet driven.

## Covered vehicles

Every appearance of these, for the player and for NPCs (holograms excepted):

- Militech Hellhound (base game and Phantom Liberty)
- Herrera Outlaw "Weiler" (Phantom Liberty)
- Rayfield Aerondight
- Thorton Galena Nomad, Quadra Type-66 Nomad, Mizutani Shion Nomad (and the Phantom Liberty courier version), Thorton Colby Nomad, Archer Quartz Nomad
- Phantom Liberty: Thorton Colby (Kurtz militia), Mahir Supron (Kurtz militia), Militech Behemoth (militia, police, NetWatch, MaxTac)

Flying vehicles are left out for now. The Rayfield Caliburn, Yaiba Semimaru, Chevalier Legatus and Chevalier Centurion have Crystal Dome effects but no dark panels, so there is nothing to add to them.

## How it works

The dark dome panels are drawn with a special effect material. Ray-traced reflections look straight through it, so a dashboard or seat reflects the street outside. For each dark panel the mod adds a copy of the panel's shape with an ordinary dark, matte material, 5 mm further out. From the seat you still see the game's own panel in front of it.

The surfaces follow the game's own dome switch: they hide the moment the dome turns on, and come back once it has finished turning off.

## Requirements

- [ArchiveXL](https://www.nexusmods.com/cyberpunk2077/mods/4198)
- [redscript](https://www.nexusmods.com/cyberpunk2077/mods/1511)

## Install

Install with a mod manager, or extract the zip into your Cyberpunk 2077 folder.

## Building

`tools/survey_dome_cars.py` finds every vehicle with a Crystal Dome and its dark panels (by material). `tools/build_archive.py` then makes the archive from the game's own files with the [WolvenKit](https://github.com/WolvenKit/WolvenKit) command line (no game files are kept in this repo). `tools/verify_archive.py` checks the result. `tools/compile.sh` test-compiles the script outside the game folder. `tools/make_zip.py` builds the zip in `dist/`.

## Credits

Built it with Claude (the AI).

[ArchiveXL](https://github.com/psiberx/cp2077-archive-xl) by psiberx, whose resource patching adds the surfaces to the car.

## Licence

MIT, see [LICENSE](LICENSE).
