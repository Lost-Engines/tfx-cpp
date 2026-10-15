# TFX C++

A native C++ reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**. The reference is the September 1994 CD release, **version 2.05**. This is early work in progress.

The original game files are required and are loaded directly from an installed copy. No extracted research assets are needed or bundled.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.30 or newer, a C++26 compiler and OpenGL development libraries. CMake uses an installed GLFW 3.4+ or fetches a pinned copy. On Debian/Ubuntu, `libglfw3-dev` and `libgl1-mesa-dev` provide the desktop dependencies.

For now this opens **a mission scene inspector**, not a playable flight simulation. It draws original terrain, assembled scenery, textures, night lights and scenery animation with a software renderer. WASD moves the camera, R/F rises/descends, arrows or right-drag look around, Shift moves faster and Escape exits. Mouse capture is released when the window loses focus.

The 320×200 image is shown at a corrected 4:3 aspect with nearest-neighbour scaling. The initial floating window uses the largest integer scale that fits the available desktop; `--scale=3` overrides this. `--mission=501` selects another mission scene.

RelWithDebInfo retains developer tools. For example, inspect a city and capture the initial scene without a window:

```sh
./build/tfx --data-dir /path/to/TFX --cell=136,114
./build/tfx --data-dir /path/to/TFX --screenshot=/tmp/tfx.ppm
```

Use `--help` for the current options. Release builds omit the developer options. Aircraft physics, moving actors, combat, menus, campaigns and audio remain to be implemented. No CI or automatic release process is configured.

```sh
ctest --test-dir build --output-on-failure
python3 tools/check_reference.py --build build --research ../tfx-reverse
```

The optional reference check compares every decoded archive entry byte for byte with the independently checked research extractor. Original game data remains external to the repository. The current executable-table reader requires the reference 2.05 `TFX.DAT` as well as `DID.DAT`.

The research tools and captures currently live in the sibling `tfx-reverse` directory. Native comparison commands, verified behaviour and current rendering limitations are in [docs/implementation.md](docs/implementation.md).

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
