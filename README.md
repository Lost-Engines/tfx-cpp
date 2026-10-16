# TFX C++

A native C++ reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**. The reference is the September 1994 CD release, **version 2.05**. This is early work in progress.

The original game files are required and are loaded directly from an installed copy. No extracted research assets are needed or bundled.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.30 or newer, a C++26 compiler and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, `libglfw3-dev` and `libgl1-mesa-dev` provide the desktop dependencies.

Direct mission launches now provide **Arcade flight** for the selected aircraft, with live steering, thrust, engines, fuel, gear and brakes. Aircraft follow their original waypoint routes and formations, including waits, takeoffs and radio calls, and can engage opposing aircraft with native weapons, guidance, damage and countermeasures; surface vehicles also follow their compiled routes, engage nearby aircraft and fire at authored ground targets. Player hits now affect the native system-fault state, and a lost aircraft follows the original disabled-flight path. Scenery executes its original animation, damage and collision programs, including terrain and runway contacts. Timed mission instructions and scheduled scenery changes run too. Target credit, completion/failure conditions and the original FINISH scripts now lead to a diagnostic mission-results screen. The default is mission 501, the first FWS engagement; `--mission=830` selects another mission.

The mouse or arrow keys steer. Hold either mouse button or `=`/`-` to change thrust. `[` and `]` toggle the engines, `G` operates the gear, `W` toggles wheel brakes and `B` operates the air brakes. Enter selects air-to-air weapons, Backspace/O selects air-to-ground weapons, and F selects the cannon/navigation mode. C cycles radar contacts or anti-radiation targets; Space fires the selected weapon. Z opens the laser designator, arrows aim it, comma/period change zoom, and another Z designates the ground point. X unlocks and F1 returns to the flight view. Carried stores use the original default loadout and pylon order, with a moving lock-on reticle for guided air-to-air missiles. `P` pauses and releases the mouse; Escape exits. See `--help` for the remaining controls and options.

The 320×200 image is shown at a corrected 4:3 aspect with nearest-neighbour scaling. The initial floating window uses the largest integer scale that fits the available desktop; `--scale=3` overrides this. Mouse capture is released on focus loss.

This is still an integration build. Complete sensor displays and crash/result artwork, aircraft-to-aircraft contacts, area flak, other flight models, automatic recovery, the complete cockpit/HUD, pilot selection, campaign progression and audio remain unfinished. The current numerical flight backend also requires a `long double` with a 64-bit significand. See [implementation status](docs/implementation.md) for precise verification boundaries.

RelWithDebInfo retains the developer scene inspector and headless captures:

```sh
./build/tfx --data-dir /path/to/TFX --presentation cdintro
./build/tfx --data-dir /path/to/TFX --menu mastopts
./build/tfx --data-dir /path/to/TFX --inspect
./build/tfx --data-dir /path/to/TFX --cell=136,114
./build/tfx --data-dir /path/to/TFX --flight-steps=100 --screenshot=/tmp/tfx.ppm
```

The presentation player runs original images, delta animations, captions and palette fades; Space finishes a caption or advances a scene, Escape skips the sequence, and Shift+Q exits. Original menu scripts can also run independently with `--menu`, including the animated main menu (`mastopts`). Other presentation graphs include `cdcolint`, `cdsomint`, `cdfwsint`, `cdyugint` and `cdyugmid`; `--language` selects briefing text. Audio remains deferred.

In the inspector, WASD moves, R/F rises/descends, arrows or right-drag look around and Shift moves faster. Release builds omit the developer options. No CI or automatic release process is configured.

```sh
ctest --test-dir build --output-on-failure
python3 tools/check_reference.py --build build --research ../tfx-reverse
```

The optional reference check compares every decoded archive entry byte for byte with the independently checked research extractor. Original game data remains external to the repository. The current executable-table reader requires the reference 2.05 `TFX.DAT` as well as `DID.DAT`.

The research tools and captures currently live in the sibling `tfx-reverse` directory. Native comparison commands, verified behaviour and current rendering limitations are in [docs/implementation.md](docs/implementation.md). The remaining work and automated verification gates are in the [implementation plan](docs/implementation-plan.md).

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
