# Crystal Dome Lighting Fix

A Cyberpunk 2077 mod for cars with a Crystal Dome. With the dome off, the panels around the cabin look solid, but with ray-traced reflections the cabin still picks up the bright world outside, as if the panels were clear glass. This mod puts a plain, opaque surface just outside each dark panel while the dome is off, so reflections stop there. When you turn the dome on, the surfaces disappear and the see-through look is as before.

**Status: test build.** Only the Militech Hellhound (Phantom Liberty, the player's car) is covered so far.

## How it works

The dark dome panels are drawn with a special effect material. Ray-traced reflections look straight through it, so a dashboard or seat reflects the street outside. For each dark panel the mod adds a copy of the panel's shape with an ordinary dark, matte material, 5 mm further out. From the seat you still see the game's own panel in front of it.

The surfaces follow the game's own dome switch: they hide the moment the dome turns on, and come back once it has finished turning off.

## Requirements

- [ArchiveXL](https://www.nexusmods.com/cyberpunk2077/mods/4198)
- [redscript](https://www.nexusmods.com/cyberpunk2077/mods/1511)

## Install

Install with a mod manager, or extract the zip into your Cyberpunk 2077 folder.

## Building

`tools/build_archive.py` makes the archive from the game's own files with the [WolvenKit](https://github.com/WolvenKit/WolvenKit) command line (no game files are kept in this repo). `tools/compile.sh` test-compiles the script outside the game folder. `tools/make_zip.py` builds the zip in `dist/`.

## Credits

Built it with Claude (the AI).

[ArchiveXL](https://github.com/psiberx/cp2077-archive-xl) by psiberx, whose resource patching adds the surfaces to the car.

## Licence

MIT, see [LICENSE](LICENSE).
