# TFX C++

A native C++ reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**. The reference is the September 1994 CD release, **version 2.05**. This is early work in progress.

The original game files are required and are loaded directly from an installed copy. No extracted research assets are needed or bundled.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.30 or newer, a C++26 compiler and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, `libglfw3-dev` and `libgl1-mesa-dev` provide the desktop dependencies.

Direct mission launches now provide **Arcade flight** for the selected aircraft, with live steering, thrust, engines, fuel, gear and brakes. Aircraft follow their original waypoint routes and formations, including waits, takeoffs and radio calls, and now acquire and manoeuvre against opposing aircraft; surface vehicles also follow their compiled routes. Scenery now executes its original animation, damage and collision programs, including terrain and runway contacts. Timed mission instructions and scheduled scenery changes also run. The default is mission 501, the first FWS engagement; `--mission=830` selects another mission.

The mouse or arrow keys steer. Hold either mouse button or `=`/`-` to change thrust. `[` and `]` toggle the engines, `G` operates the gear, `W` toggles wheel brakes and `B` operates the air brakes. `P` pauses and releases the mouse; Escape exits. See `--help` for the remaining controls and options.

The 320×200 image is shown at a corrected 4:3 aspect with nearest-neighbour scaling. The initial floating window uses the largest integer scale that fits the available desktop; `--scale=3` overrides this. Mouse capture is released on focus loss.

This is still an integration build. Moving-object collision, the full damage/death lifecycle, other flight models, automatic recovery, air combat and projectiles, the complete cockpit/HUD, menus, campaign progression and audio remain unfinished. The current numerical flight backend also requires a `long double` with a 64-bit significand. See [implementation status](docs/implementation.md) for precise verification boundaries.

RelWithDebInfo retains the developer scene inspector and headless captures:

```sh
./build/tfx --data-dir /path/to/TFX --inspect
./build/tfx --data-dir /path/to/TFX --cell=136,114
./build/tfx --data-dir /path/to/TFX --flight-steps=100 --screenshot=/tmp/tfx.ppm
```

In the inspector, WASD moves, R/F rises/descends, arrows or right-drag look around and Shift moves faster. Release builds omit the developer options. No CI or automatic release process is configured.

```sh
ctest --test-dir build --output-on-failure
python3 tools/check_reference.py --build build --research ../tfx-reverse
```

The optional reference check compares every decoded archive entry byte for byte with the independently checked research extractor. Original game data remains external to the repository. The current executable-table reader requires the reference 2.05 `TFX.DAT` as well as `DID.DAT`.

The research tools and captures currently live in the sibling `tfx-reverse` directory. Native comparison commands, verified behaviour and current rendering limitations are in [docs/implementation.md](docs/implementation.md). The remaining work and automated verification gates are in the [implementation plan](docs/implementation-plan.md).

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
