# TFX C++

A native C++ reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**. The reference is the September 1994 CD release, **version 2.05**. This is early work in progress.

The original game files are required and are loaded directly from an installed copy. No extracted research assets are needed or bundled.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.30 or newer, a C++26 compiler and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, `libglfw3-dev` and `libgl1-mesa-dev` provide the desktop dependencies.

Normal startup plays the original introduction and opens pilot enrolment and the main menu; `--skip-intro` goes straight to enrolment. Pilot slots use the original `TFXSAV.0`–`TFXSAV.9` format in the selected installation directory. Training briefings now lead into flight and resume the authored sequence after mission results. Tour of Duty briefings show their original maps and route review; Space or the right mouse button advances a note, and flight starts after the review. Mission authoring and some campaign screens remain unfinished.

Before takeoff, the original arming screen lets you choose stores and place them on compatible mounts. Paired mounts fill together; right-click ends placement. Use **DEFAULT** for the mission's preset or **DONE** to fly. Escape also leaves the screen.

Direct mission launches provide the original **Arcade, Simple, Military-spec and Realistic flight models** for the selected aircraft, with live steering, thrust, engines, fuel, gear and brakes. Aircraft follow their original waypoint routes and formations, including waits, takeoffs and radio calls, and can engage opposing aircraft with native weapons, guidance, damage and countermeasures; surface vehicles also follow their compiled routes, engage nearby aircraft and fire at authored ground targets. Player hits now affect the native system-fault state, and a lost aircraft follows the original disabled-flight path, with the authored crash, splash and solid-impact explosion animations and loss cameras. Scenery executes its original animation, damage and collision programs, including terrain and runway contacts. Timed mission instructions and scheduled scenery changes run too. Aircraft impacts, weapon hits and CBU blasts show their original animated effects; authored flak regions produce daytime bursts and nighttime fire. Enemy tracking/fire drives the original weapons authorization and warnings; unauthorized ground attacks also produce the original training warnings and orders penalties. Target credit, completion/failure conditions and the original FINISH scripts now return automatically to the authored campaign presentations. Direct mission launches retain a diagnostic results screen. Use `--mission=501` to enter the first FWS engagement directly, or choose another mission number.

Startup reads the original `TFX.CFG`; `--flight-model` overrides its model selection. Without a configuration, Arcade is selected. The mouse or arrow keys steer in Arcade. Select `--flight-model=simple`, `--flight-model=military-spec` or `--flight-model=realistic` for the other original models, using arrow keys and Alt+left/right for rudder. These retain their different flight dynamics, aircraft-specific handling, gear damage and carrier arrestor behaviour. `--control=keyboard`, `--control=mouse` or `--control=joystick` overrides the configured input. Simple supports keyboard/joystick steering; joystick steering is available in the three non-Arcade models. `--joystick=N` selects a particular device (0–15), otherwise the first available stick is used. An absent stick falls back to keyboard input.

Joystick buttons follow the original mapping: fire, select ground weapons, select air weapons and cycle targets on buttons 1–4. Stick sensitivity uses the original `JOYSCALE` setting.

Press **backtick** in flight for the original configuration and realism menus. Changes take effect when you return to the game, and preferences are saved to the installation’s `TFX.CFG`. The dialogs include flight model, controls, joystick sensitivity, world detail, recovery and realism settings. The sound switch controls the original sampled effects and speech. Sound Blaster FM music follows the original `MUSIC` setting, and `--music=soundblaster-fm` selects it explicitly. For Roland LAPC-I music, use `--music=roland-lapc --rom-dir=/path/to/roms` with compatible CM-32L/MT-32 control and PCM ROMs. `--music=none` disables music. The original Sound Canvas setting uses SCC-1A emulation; `--music=roland-scc1a` or `--music=roland-sc55` selects the available hardware model, with its matching ROMs in `--rom-dir`. These are compatible alternatives to the original SCC-1, whose exact ROM set is unavailable. Flight music now uses the original theme selection, temporary cues and engine sounds, including engine playback with music switched off. CD playback remains deferred; the explicit FM option selects the synthesised path.

`A` toggles autopilot. `7` selects waypoint following, `8` heading/altitude hold, `9` aircraft tracking and `0` speed hold. Arrow keys adjust applicable autopilot targets; `=`/`-` adjust target speed. `6` restores cruise speed, `5` toggles automatic stick pressure and Tab requests recovery. Alt+L requests automatic landing at the selected runway or carrier. Cockpit control displays show the live autopilot, flaps and F-22 thrust-vectoring state.

Hold either mouse button or `=`/`-` to change thrust. `[` and `]` toggle the engines, `G` operates the gear, `H` toggles the arrestor hook, `W` toggles wheel brakes and `B` operates the air brakes. Keypad `*` increases afterburner; Alt+keypad `*` or keypad `-` decreases it. Enter selects air-to-air weapons, Backspace/O selects air-to-ground weapons, and F selects the cannon/navigation mode. C cycles radar contacts or anti-radiation targets; Space fires the selected weapon. Insert releases chaff and Delete releases flares. On the F-117 and F-22, E toggles ECM and S toggles stealth; enabling one turns the other off.

Apostrophe toggles aerial refuelling: the nearest allied tanker supplies the original contact cues, connection behaviour and fuel transfer. I/backslash toggles the original instrument landing system, with approach-beacon and runway/glide-slope guidance. Z opens the laser designator, arrows aim it, comma/period change zoom, and another Z designates the ground point. X unlocks and F1 returns to the flight view. Direct `--mission` launches use the mission's default stores; normal campaign launches use your chosen loadout. Weapons retain the original pylon order, with a moving lock-on reticle for guided air-to-air missiles. The original forward HUD shows flight readings, heading/pitch scales, NAV/AA/AG weapon sights, cannon trajectory and bomb-impact prediction. Selected aircraft show their original telemetry and acquisition/lock cues; designated ground targets use the original outline. `Page Up`/`Page Down` raise and lower the original cockpit. `1`/`2`/`3` cycle the original MFDs, `R` changes radar range, and `N` selects the ground-target preview. The displays show live stores, fuel/range, systems, moving maps and radar contacts; FLIR/DLIR and ground-target previews use the current software scene renderer. Radio calls scroll through their original cockpit display; `L` replays the last message. `P` pauses and releases the mouse. Press Escape twice to eject; the seat animation, parachute descent and recovery region determine the pilot’s result. Escape after ejection ends the flight. Shift+Q quits the current run. See `--help` for the remaining controls and options.

`F1` restores the cockpit; Shift+F1 gives a full forward view. `F2`/`F3` turn your head, `F4` looks behind, `F5` follows the aircraft, `F6` places a fly-past camera, `F7` selects tactical view, `F8` follows the latest fired store (press twice for its nose view), `F9` observes a target and `F10` enters the virtual cockpit/target-tracking view. Shift+arrow keys move the view. The virtual cockpit uses the original canopy and static instrument textures. External views show the original altitude, speed and heading strip. Shift+N toggles the original infrared night vision; the laser designator and fired-store nose view also select their original infrared palette. Altitude-based colours follow the original environment palettes; startup uses the saved `HUDCOL` intensity and Y/U adjust it. Weather and some view artwork remain in progress.

The 320×200 image is shown at a corrected 4:3 aspect with nearest-neighbour scaling. The initial floating window uses the largest integer scale that fits the available desktop; `--scale=3` overrides this. Mouse capture is released on focus loss.

This is still an integration build. Complete sensor displays and remaining visual effects/result artwork, remaining aircraft contact cases, flak cockpit shake, the remaining HUD cues, complete campaign progression and the remaining music devices/triggers remain unfinished. The numerical flight backend currently requires x87 support; it preserves the original startup precision within flight calculations. See [implementation status](docs/implementation.md) for precise verification boundaries.

RelWithDebInfo retains the developer scene inspector and headless captures:

```sh
./build/tfx --data-dir /path/to/TFX --presentation cdintro
./build/tfx --data-dir /path/to/TFX --menu mastopts
./build/tfx --data-dir /path/to/TFX --inspect
./build/tfx --data-dir /path/to/TFX --cell=136,114
./build/tfx --data-dir /path/to/TFX --flight-steps=100 --screenshot=/tmp/tfx.ppm
```

The presentation player runs original images, delta animations, captions and palette fades; Space finishes a caption or advances a scene, Escape skips the sequence, and Shift+Q exits. Original menu scripts can also run independently with `--menu`, including the animated main menu (`mastopts`). Other presentation graphs include `cdcolint`, `cdsomint`, `cdfwsint`, `cdyugint` and `cdyugmid`; `--language` selects briefing text. Presentations retain their synthesised music requests; CD playback remains deferred.

In the inspector, WASD moves, R/F rises/descends, arrows or right-drag look around and Shift moves faster. Release builds omit the developer options. No CI or automatic release process is configured.

```sh
ctest --test-dir build --output-on-failure
python3 tools/check_reference.py --build build --research ../tfx-reverse
```

The optional reference check compares every decoded archive entry byte for byte with the independently checked research extractor. Original game data remains external to the repository. The current executable-table reader requires the reference 2.05 `TFX.DAT` as well as `DID.DAT`.

The research tools and captures currently live in the sibling `tfx-reverse` directory. Native comparison commands, verified behaviour and current rendering limitations are in [docs/implementation.md](docs/implementation.md). The remaining work and automated verification gates are in the [implementation plan](docs/implementation-plan.md).

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
