# Reconstruction and verification

Reference: TFX 2.05, September 1994 CD. Native offsets refer to `TFX.DAT`, SHA-256 `2cc41a39fa95a2c9fd883c4220d7bdd9cca00c543c89b019eb270763f59d1d9a`.

## Working boundaries

* `DID.DAT` index, native filename substitution/hash, raw and RA v2 resources load directly from the selected installation.
* All 3,488 reference archive entries compare byte for byte against did-unpack (2,416 RA-compressed and 1,072 raw); malformed input is tested without game data.
* All 1,012 model programs decode directly from the archive. The C++ VM matches the checked inspection interpreter in 2,042 detail/state cases (253,334 vertices). This establishes program interpretation, not native camera/raster equivalence.
* All 703 valid SSD definitions match their decoded initial parts, anchored draw calls and parameter streams. All 1,440,000 cells across 36 grid/lighting combinations match their tile IDs and deterministic inspection variant choices. Actor initialiser random side effects are not yet simulated.
* Original x86 calls independently verify 1,332 condition predicates, 205 component matrices and 64 world random updates. All 1,024 regenerated sine samples match the executable, including the -32766 negative peak.
* Native comparisons cover 1,260 animation-clock frames, 126 completed parameter-stream updates and 48 multi-vertex jitter cases. A non-returning synthetic stream is rejected explicitly rather than counted as a successful update.
* All 128 retail mission scene selections, signed starting coordinates and optional aircraft assignments match their source metadata, and every initial scene renders successfully. Five original-code captures verify the separation of regional terrain from weather/lighting configuration.
* No audio, campaign execution or flight simulation is implemented yet.

## Verification approach

Each subsystem needs evidence from the original code: controlled calls with declared memory/inputs, output and side-effect capture, then the same cases through C++. Preserve timing, random seeds and external callback results for sequence tests. Integer results should match exactly; numerical tolerances for x87-derived calculations require explicit justification and checks of resulting branches/state transitions.

Use isolated native calls first, subsystem sequences next, and instrumented DOSBox traces for behaviour requiring complete mission context. Research-viewer approximations are inspection aids, not proof of native gameplay behaviour.

The developer probe streams decoded resources to the reference checker over a pipe. Nothing is extracted into the installation or copied into the repository.

## Reproducing the analytical checks

```sh
python3 tools/check_native.py --build build --data-dir /path/to/TFX
python3 tools/check_shapes.py --build build --research ../tfx-reverse
python3 tools/check_world.py --build build --research ../tfx-reverse
python3 tools/check_world_selection.py --research ../tfx-reverse
python3 tools/check_mission_scenes.py --build build --research ../tfx-reverse
```

`check_native.py` and `check_world_selection.py` need Unicorn and the original reference executable. They execute bounded original routines in isolated x86 memory with controlled stack/register/global inputs; DOS, game startup and installation files are not modified. The shape/world comparisons additionally need the research tree and Node.js, and explicitly distinguish inspection comparisons from native execution.

## Software scene inspection

The executable loads regional geometry from the mission’s `world` and palette/night settings from its separate `type` declaration. The original world loader truncates filenames to eight characters, so `yugoslavia` selects `lev/yugoslav.*`. The similarly named weather grids remain available through the developer `--grid` override; they are not substituted for the actual regional terrain. This also avoids the out-of-table IDs in the retained `colum_d` and `somal_st` grids without inventing a repair.

Numeric start Y values already use signed native world coordinates. `landed` is retained as a separate state; only the inspection camera substitutes an elevated viewpoint. Omitted aircraft choices remain unspecified, ready for the mission runtime to inherit rather than silently selecting a craft.

The executable loads the original palette, complete SSD model parts, native world scales, tile headings and anchored placements. Whole models paint in camera-depth order plus the signed header bias; each model retains its authored primitive sequence and facing branches. CPU drawing keeps palette indices through flat/shaded spans, affine textures, transparent index-zero texels, lines, fixed-size night lights and sized circles. Original circle tables are read from the selected 2.05 executable as data; no game instructions run inside the application.

Native comparison captures verify all nine complete circle rasters, 27 drawing-mode interiors (43,200 pixels), three procedural seed transitions, 44 rounded-corner recurrences and 1,280 Gouraud samples:

```sh
python3 tools/check_raster.py --build build --research ../tfx-reverse
```

The scene inspector is an integration milestone, not a claim of full native renderer fidelity. Its free camera uses floating projection with six clipping planes, its general polygon boundaries use half-open spans, and its scene collection currently uses the nearest polygon detail level. Native fixed-point world-camera setup, exact clipped raster boundaries, runtime palette remaps/fades, weather/horizon effects, dynamic entities and actor-bound textures still need implementation and verification. The simplified horizon and camera movement are explicitly inspection aids. Original actor initialisers can consume additional random values; current tile variants use the checked deterministic inspection sequence.

The display follows Darker's GLFW/OpenGL 2.1 presentation approach: nearest-neighbour upload of a CPU image, 4:3 aspect correction, integer enlargement and a floating window fitted to the work area. Wayland sizing obtains the compositor's maximised area, restores the window and chooses the fitting scale. OpenGL performs no game-world drawing. The first scene is presented before the focus gate: Wayland needs an attached buffer before it can map and focus the window, so waiting for focus first deadlocks startup. Automated Xvfb tests clear `WAYLAND_DISPLAY` so they cannot accidentally open on the user's desktop.

## Scenery animation

Every visited cell owns its part parameters and stream cursors; cached definitions remain immutable. The original PIT divisor gives 54.6204 timer ticks per second. The native signed-word gate subtracts seven only when the accumulator is greater than seven, permits at most one animation update per displayed frame, and clears an excessive backlog. This gives a nominal 7.8029 animation updates per second, with the original frame-rate dependence retained.

Parameter programs preserve byte wrapping, comparisons, relative jumps, held endpoints and per-definition selector eligibility. An SSD event is an explicit request: until the actor dispatcher exists, the inspector pauses that stream and records a diagnostic. It does not invent the event’s effect. Vertex jitter uses its own native ADD/ADC sequence and a seed held between animation updates, independently of terrain-variant randomness.

These checks establish the local clock, interpreter and jitter arithmetic. Full actor visibility/update eligibility, mission events, random consumption by original initialisers and dynamic actors remain separate work. The runtime still uses the initial intact SSD draw assembly.

## Local build validation

Both RelWithDebInfo and Release have been built with GCC 16.2 in C++26 mode. An AddressSanitizer/UndefinedBehaviorSanitizer build passes the resource/animation boundary tests, all 128 initial mission scene renders and the byte-exact 3,488-resource comparison. Isolated X11 desktop smoke checks cover the 640×480 scale-2 window, keyboard exit and exclusion of developer options from Release. Other desktop platforms have not yet been built or tested.

The optional `python3 tools/check_wayland_window.py --build build --data-dir /path/to/TFX` regression check starts a private headless Sway compositor and verifies a visible initial frame and clean window close at automatic and explicit scaling, without a keyboard device or initial focus. It does not connect to the desktop session. The previous startup order times out in this check before any scene buffer is submitted.
