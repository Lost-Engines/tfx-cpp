# TFX C++

A native C++26 reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**, using the September 1994 CD release, **version 2.05**, as its reference.

[TFX Redux](https://github.com/Lost-Engines/tfx-redux) builds on this reconstruction with higher resolutions, adjustable field of view and draw distance, and arming-screen improvements. This repository preserves the original presentation and behaviour.

The supplied fetch script downloads the reference game CD and audio firmware. You can also use your own TFX 2.05 installation. Research exports are neither required nor bundled.

## Getting started

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./scripts/fetch-assets.sh
./build/tfx
```

Requires CMake 3.30+, a compiler and standard library with C++26 support, and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, install `libglfw3-dev` and `libgl1-mesa-dev` for the desktop dependencies. The faithful numerical flight backend currently requires x87 support.

The default installation directory is `~/.local/share/tfx` on Linux/macOS
(`$XDG_DATA_HOME/tfx` when set), or beside `tfx.exe` on Windows. The fetch
script uses that location too. An installation in the current directory takes
precedence; `--data-dir` selects a different location.

On first launch, the fetched disc supplies the required game files automatically. Later launches also repair missing or changed files from that disc, preserving settings and pilot saves. No DOS installer or 7-Zip extractor is needed.

An existing installation can be selected with `--data-dir /path/to/TFX`. It needs the reference `TFX.DAT` and `DID.DAT`. Keep `START.EXE`
there for synthesised music, and `GUS.COM` for Gravis effects. Existing `TFX.CFG`
settings are read on startup. Pilot saves and configuration changes use the
selected installation directory, which should be writable.

Normal startup plays the introduction and opens pilot enrolment. `--skip-intro` goes straight to enrolment. To try a mission directly:

```sh
./build/tfx --mission=501
```

Mission 501 is the first Fighter Weapons School engagement. Direct launches use the mission’s preset stores; campaign launches open the original arming screen. Choose **DEFAULT** for its preset, then **DONE** to fly.

## Playing

The original menus, briefings, mission planning, arming, flight, combat and results are connected. All four flight models are available, along with the original cockpit/MFDs, cameras, weather, damage, refuelling and automatic landing. Landing and stopping can refuel, repair and rearm your aircraft through the original arming screen. Campaign flights return to the authored presentations and retain DOS-compatible `TFXSAV.0`–`TFXSAV.9` pilot files.

Arcade uses mouse steering. The other flight models support keyboard and joystick controls; `--flight-model` and `--control` override the saved choices. Press **backtick** in flight for configuration and realism settings, and **P** to pause. Press Escape twice to eject; **Shift+Q** opens the quit/enrol confirmation.

**Alt+V** starts or stops a flight recording. Its default filename is `video.rec`, editable in the configuration menu. A new recording replaces that file. After a campaign flight, the original WNN sequence and recorded flight play automatically.

The 320×200 image uses nearest-neighbour scaling and square pixels. The initial floating window chooses the largest integer scale that fits the desktop; `--scale=3` overrides it. Focus loss releases mouse capture.

See [controls and configuration](docs/controls.md) for weapons, autopilot, cameras, MFDs, joystick bindings, recordings and developer commands. The original manual remains the best guide to flying the missions.

## Sound

Sampled Sound Blaster and Gravis effects and speech, FM music, Roland LAPC-I and Sound Canvas emulation are connected. The saved `SOUNDFX=4` setting selects Gravis; `SOUNDFX=2` with `MUSIC=2` selects the original LAPC-I synthesised flight effects. `--music=soundblaster-fm` selects synthesised FM music explicitly; `--music=none` disables music. Roland modes find matching ROMs automatically beside the game files or in the default installation directory. Details are in [controls and configuration](docs/controls.md).

QSound spatial processing is built in and enabled automatically for Sound Blaster effects. It needs no firmware download. `--qsound=off` selects ordinary mono output; `--qsound=on` explicitly requires Sound Blaster effects to be selected. This uses the recovered original filters with endpoint-clamped positioning; exact sound-card arithmetic remains unverified. Music and CD playback are unaffected.

To fetch or repair the game disc and audio firmware on Linux or macOS:

```sh
./scripts/fetch-assets.sh
./build/tfx --music=roland-scc1a
```

On Windows, run `scripts\fetch-assets.bat`. The scripts use the default
installation directory described above, so no `--rom-dir` option is needed.
They fetch the reference CD as individual BIN files (roughly 576 MiB), plus
CM-32L/LAPC-I, SC-55 v1.21 and SCC-1A v1.30 ROMs. Every file is checked on each
run; missing or damaged files are downloaded again, with retries. An optional destination argument and
`--rom-dir` are available for custom locations. Linux/macOS
needs `curl`, `unzip` and `sha256sum` or `shasum`; Windows uses its built-in
`curl.exe`, `certutil.exe` and `tar.exe`.

The fetched installation defaults to **CD music**, streamed directly from its
`cd/tfx.cue` and BIN files. An existing installation’s saved music choice is
retained; `--music=soundblaster-cd` (or `--music=cd`) selects CD playback.

To use another disc image or your own ripped tracks:

```sh
./build/tfx --cd-cue /path/to/tfx.cue
./build/tfx --cd-audio-dir /path/to/soundtrack
```

Rips can be FLAC, Ogg Vorbis, MP3 or WAV, named `track02.flac`, `track03.ogg`,
and so on, using the original physical CD track numbers (audio starts at 02).
Names such as `track-02` and uppercase extensions are also accepted. Playback
uses the original track selection, stop and flight-loop behaviour.

## Development status

The original and C++ launch/flight loops match across all 128 retail mission setups and their first sixteen Arcade frames. Longer controlled comparisons cover successful interception and ground attack, incoming fire and aircraft loss, refuelling, mission return, ejection and recording. Subsystem checks execute the original code independently, with compact regressions runnable without game data:

```sh
ctest --test-dir build --output-on-failure
```

For a minimal installation, `cmake --install build-rel --component Runtime --prefix /path/to/output` copies the executable and the matching platform’s fetch script and asset manifests from a Release build. Original game data and ROMs remain separate.

The [verification matrix](docs/verification.md) distinguishes complete-session evidence, persistent campaign checks and long-session audio/lifetime coverage. [Implementation notes](docs/implementation.md) retain the research details. The research tree is the sibling `tfx-reverse` directory.

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
