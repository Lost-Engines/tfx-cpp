# TFX C++

A native C++ reconstruction of Digital Image Design’s **TFX: Tactical Fighter Experiment**. The reference is the September 1994 CD release, **version 2.05**. This is early work in progress.

The original game files are required and are loaded directly from an installed copy. No extracted research assets are needed or bundled.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j
./build/tfx --data-dir /path/to/TFX
```

Requires CMake 3.28 or newer and a C++23 compiler. There is no CI or automatic release process yet.

```sh
ctest --test-dir build --output-on-failure
python3 tools/check_reference.py --build build --research ../tfx-reverse
```

The optional reference check compares every decoded archive entry byte for byte with the independently checked research extractor. Original game data remains external to the repository.

Research: [tfx-reverse](https://github.com/Lost-Engines/tfx-reverse). Development and verification notes are in [docs/implementation.md](docs/implementation.md).

GPL-3.0-or-later; see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
