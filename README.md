# TFX C++

A native C++26 reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**, using the September 1994 CD release, **version 2.05**, as its reference. This is an integration build under active verification.

You need the original installed game files. They are loaded directly; extracted research assets are neither required nor bundled.

## Getting started

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.30+, a compiler and standard library with C++26 support, and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, install `libglfw3-dev` and `libgl1-mesa-dev` for the desktop dependencies. The faithful numerical flight backend currently requires x87 support.

Select the directory containing the reference `TFX.DAT` and `DID.DAT`. Keep `START.EXE` there for synthesised music, and `GUS.COM` for Gravis effects. Existing `TFX.CFG` settings are read on startup. Pilot saves and configuration changes use the selected installation directory, which should be writable.

Normal startup plays the introduction and opens pilot enrolment. `--skip-intro` goes straight to enrolment. To try a mission directly:

```sh
./build/tfx --data-dir /path/to/TFX --mission=501 --music=soundblaster-fm
```

Mission 501 is the first Fighter Weapons School engagement. Direct launches use the mission’s preset stores; campaign launches open the original arming screen. Choose **DEFAULT** for its preset, then **DONE** to fly.

## Playing

The original menus, briefings, mission planning, arming, flight, combat and results are connected. All four flight models are available, along with the original cockpit/MFDs, cameras, weather, damage, refuelling and automatic landing. Campaign flights return to the authored presentations and retain DOS-compatible `TFXSAV.0`–`TFXSAV.9` pilot files.

Arcade uses mouse steering. The other flight models support keyboard and joystick controls; `--flight-model` and `--control` override the saved choices. Press **backtick** in flight for configuration and realism settings, and **P** to pause. Press Escape twice to eject; **Shift+Q** opens the quit/enrol confirmation.

**Alt+V** starts or stops a flight recording. Its default filename is `video.rec`, editable in the configuration menu. A new recording replaces that file. After a campaign flight, the original WNN sequence and recorded flight play automatically.

The 320×200 image uses nearest-neighbour scaling and corrected 4:3 proportions. The initial floating window chooses the largest integer scale that fits the desktop; `--scale=3` overrides it. Focus loss releases mouse capture.

See [controls and configuration](docs/controls.md) for weapons, autopilot, cameras, MFDs, joystick bindings, recordings and developer commands. The original manual remains the best guide to flying the missions.

## Sound

Sampled Sound Blaster and Gravis effects and speech, FM music, Roland LAPC-I and Sound Canvas emulation are connected. The saved `SOUNDFX=4` setting selects Gravis; `SOUNDFX=2` with `MUSIC=2` selects the original LAPC-I synthesised flight effects. `--music=soundblaster-fm` selects synthesised FM music explicitly; `--music=none` disables music. Roland modes require the matching ROMs selected with `--rom-dir`. Details are in [controls and configuration](docs/controls.md).

CD music remains deferred. The original hybrid SB/CD setting can request CD playback; select FM explicitly to use synthesised flight music instead.

## Development status

The original and C++ launch/flight loops match across all 128 retail mission setups and their first sixteen Arcade frames. Longer controlled comparisons cover successful interception and ground attack, aircraft loss, mission return, ejection and recording. Subsystem checks execute the original code independently, with compact regressions runnable without game data:

```sh
ctest --test-dir build --output-on-failure
```

Broader campaign/encounter coverage and the remaining optional audio paths are still being investigated. [Verification details](docs/implementation.md) distinguish complete-session evidence from isolated checks; the [implementation plan](docs/implementation-plan.md) tracks remaining work. The research tree is the sibling `tfx-reverse` directory.

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
