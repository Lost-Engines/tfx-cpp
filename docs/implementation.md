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
* A headless timing replay matches 4,096 original-code frames, including timer polling, filtered float/timestep double bits, previous-frame animation gating and ordered projectile substeps. This is a subsystem sequence with declared external inputs, not a complete flight session.
* The complete native mission-script loader agrees with typed C++ INIT results for all 128 retail missions in two prior-state contexts (256 setups), including target/message text, speed bits, timing, flak and scenery-event declarations. Resource/actor creation and FINISH execution are outside this capture.
* All 128 retail FINISH programs agree with original execution across 8,192 supplied result states: scoring, signed-word conditions, target flags, branch/return handling and campaign statistics. Combat itself and persistent campaign/front-end execution are not implemented.
* Carried-store mass, drag, both moment contributions and aircraft-specific fuel capacity match the original x87 routine bit for bit in 1,197 loadouts, including every store/aircraft/slot combination and fractional mixed mounts.
* Arcade aircraft motion is translated and checked against original execution (details below); audio and complete flight sessions remain outstanding.

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

## Integrated scene and flight display

The executable loads regional geometry from the mission’s `world` and palette/night settings from its separate `type` declaration. The original world loader truncates filenames to eight characters, so `yugoslavia` selects `lev/yugoslav.*`. The similarly named weather grids remain available through the developer `--grid` override; they are not substituted for the actual regional terrain. This also avoids the out-of-table IDs in the retained `colum_d` and `somal_st` grids without inventing a repair.

Numeric start Y values already use signed native world coordinates. `landed` is retained as a separate state; only the inspection camera substitutes an elevated viewpoint. The literal scene metadata retains an omitted aircraft as unspecified. Original-loader execution now establishes that INIT resets the runtime aircraft to Eurofighter before reading any explicit `plane` command; it is not inherited wholesale from the preceding mission.

The executable loads the original palette, complete SSD model parts, native world scales, tile headings and anchored placements. Whole models paint in camera-depth order plus the signed header bias; each model retains its authored primitive sequence and facing branches. CPU drawing keeps palette indices through flat/shaded spans, affine textures, transparent index-zero texels, lines, fixed-size night lights and sized circles. Original circle tables are read from the selected 2.05 executable as data; no game instructions run inside the application.

Native comparison captures verify all nine complete circle rasters, 27 drawing-mode interiors (43,200 pixels), three procedural seed transitions, 44 rounded-corner recurrences and 1,280 Gouraud samples:

```sh
python3 tools/check_raster.py --build build --research ../tfx-reverse
```

The direct flight view uses the player’s verified Q15 basis and floating projection with six clipping planes. The developer inspector retains its free camera. Neither path claims full native renderer fidelity; its general polygon boundaries use half-open spans, and its scene collection currently uses the nearest polygon detail level. Native fixed-point world-camera setup, exact clipped raster boundaries, runtime palette remaps/fades, weather/horizon effects, dynamic entities and actor-bound textures still need implementation and verification. The simplified horizon and camera movement are explicitly inspection aids. Original actor initialisers can consume additional random values; current tile variants use the checked deterministic inspection sequence.

The display follows Darker's GLFW/OpenGL 2.1 presentation approach: nearest-neighbour upload of a CPU image, 4:3 aspect correction, integer enlargement and a floating window fitted to the work area. Wayland sizing obtains the compositor's maximised area, restores the window and chooses the fitting scale. OpenGL performs no game-world drawing. The first scene is presented before the focus gate: Wayland needs an attached buffer before it can map and focus the window, so waiting for focus first deadlocks startup. Automated Xvfb tests clear `WAYLAND_DISPLAY` so they cannot accidentally open on the user's desktop.

## Scenery animation

Every visited cell owns its part parameters and stream cursors; cached definitions remain immutable. The original PIT divisor gives 54.6204 timer ticks per second. The native signed-word gate subtracts seven only when the accumulator is greater than seven, permits at most one animation update per displayed frame, and clears an excessive backlog. This gives a nominal 7.8029 animation updates per second, with the original frame-rate dependence retained.

Parameter programs preserve byte wrapping, comparisons, relative jumps, held endpoints and per-definition selector eligibility. Animation events now execute the instance’s SSD entry and resume the same selector immediately, including stream replacement. Vertex jitter uses its own native ADD/ADC sequence and a seed held between animation updates, independently of terrain-variant randomness.

These checks establish the local clock, interpreter and jitter arithmetic. Full actor visibility/update eligibility, mission events, random consumption by original initialisers and dynamic actors remain separate work. The runtime now executes entry 1 for its current draw assembly, including damaged model and overlay selection.

## Mission declarations

```sh
python3 tools/check_initialisation.py --build build --research ../tfx-reverse
```

`missions::initialise` produces typed starting state, angles, aircraft/loadout selection, targets, completion declarations, flak regions, timed messages and scheduled scenery events. Direct mission entry validates and uses this setup, including native actor population creation. It stops before FINISH; it does not simulate the declared conditions or events. Unsupported INIT commands fail explicitly.

The native comparison executes original `0x7a4f8`, including its reset sequence, label search, command dispatch, text readers and numeric handlers. Only decoded-source delivery, allocation/release, environment asset setup and the optional saved-start request are intercepted. Those boundaries are declared in the capture. Fresh and seeded-state runs cover every retail script. Omitted `plane` resets to Eurofighter and angles reset to zero; omitted speed/loadout and a `landed` start's untouched height retain supplied prior values. The caller's complete initial state and any subsequent saved-start override remain to be reconstructed.

Text keeps native CRLFs while removing leading indentation per line. Authored seconds use **54 ticks**, distinct from the launcher's actual 54.6204 Hz clock. Target cells become centred world positions using the same 2,048-unit cell contract. Native target/flak/message/event limits are named beside their owning structures. SETBOB stores an SSD event entry and the target cell coordinates: native `0x70db0` resolves its handle and `0x70e44` dispatches the entry after the scheduled time. Static terrain targets now resolve at startup, and the live mission timeline dispatches their entries at the original frame boundary. Attached scenery actors remain a separate integration path.

## Mission result rules

```sh
python3 tools/check_rules.py --build build --research ../tfx-reverse
```

`finish_program` compiles retail FINISH statements into typed predicates, assignments, branches and returns. Result counters and target life states are explicit inputs; campaign variables are a separate declared table. This permits analytical mission-result checks before aircraft, weapons and damage produce those inputs. It is not a substitute for subsequent end-to-end combat comparisons.

The reference executes original `0x7ae80`, its parser and variable lookup, and its target destroyed-flag reader. Synthetic target records and their handle resolution are supplied; optional saved-start persistence is intercepted. The check compares all seven supplied campaign variables after every case, including common statistics updated outside the script. Each of the 128 retail programs receives 64 cases, varying completed state and friendly losses independently of enemy counts, plus target combinations, signed-word boundaries and score overflow. Generated captures can be retained with `--record build/native-rules.json`.

Several native behaviours require deliberate preservation:

* Numeric predicates compare the **signed low 16 bits**, while assignments and score accumulation use wrapping 32-bit values.
* AND/OR terms evaluate left to right without conventional precedence or short-circuiting.
* The common finish handoff credits `pairscore` before the authored script. Most retail scripts add it again; the reconstruction retains both additions.
* RETURN immediately ends the result program. The existing mission-result variable survives if no RETURN changes it; its final nonzero value controls the completed-mission counter.
* Original brace cleanup can skip a following sibling block after a braced IF. This matters in `miss605`: with `completed == 1`, a failed inner `eplanes_down == 10` test skips the next `eplanes_down > 0` block. The native result is zero in the captured partial-success cases. A conventional structured interpretation would award a different score/result.

These claims cover the retail grammar and the declared original-call boundary. Other retained authoring scripts and broader parser dialects remain separate work. The class does not write pilots, run campaign graphs or infer combat outcomes.

## Carried-store flight effects

```sh
python3 tools/check_stores.py --build build --data-dir /path/to/TFX
```

The ten-slot loadout has explicit occupancy, mass, drag, tank classification and mount position. `flight::accumulate_stores` preserves the original slot order, double stores after each contribution, and extended intermediates within each contribution. The two moment groupings retain neutral A/B names until the complete flight-coordinate convention identifies their physical axes. Vectorstorm supplies the corresponding squared vector lengths.

The original routine `0x95dc8` executes without intercepted dependencies. Tests use all 27 original store records, all three native aircraft presets' mount positions, each of the ten slots, empty loadouts and fractional mixed mounts: **1,197 exact stored-bit comparisons per build**. A tank sets the presence flag for any aircraft, but the capacity multiplier applies only to Eurofighter. The subsystem does not yet apply changing stores to an integrated flight trajectory.

The current arithmetic backend requires `long double` with a 64-bit significand, matching the controlled x87 precision used in these captures. Other formats fail explicitly if this subsystem is called; its unit test reports a platform skip. Native scene inspection does not call it. A portable equivalent and the original startup FPU environment still need to be established before claiming flight fidelity on other architectures. Ordinary `double` is not substituted silently.

## Local build validation

Both RelWithDebInfo and Release have been built with GCC 16.2 in C++26 mode. An AddressSanitizer/UndefinedBehaviorSanitizer build passes all six boundary suites, all 128 initial mission scene renders and the byte-exact 3,488-resource comparison. Isolated X11 desktop smoke checks cover the 640×480 scale-2 window, keyboard exit and exclusion of developer options from Release. Other desktop platforms have not yet been built or tested.

The optional `python3 tools/check_wayland_window.py --build build --data-dir /path/to/TFX` regression check starts a private headless Sway compositor and verifies a visible initial frame and clean window close at automatic and explicit scaling, without a keyboard device or initial focus. It does not connect to the desktop session. The previous startup order times out in this check before any scene buffer is submitted.

## Simulation timing and headless replay

```sh
python3 tools/check_timing.py --build build --data-dir /path/to/TFX
```

This check needs Unicorn and the original September 1994 executable; it does not need the research tree. `tools/native_reference.py` relocates its LE objects, supplies flat selectors and a controlled x87 environment, and requires each call to reach its return address within an instruction budget. Unmapped dependencies and DOS interrupts fail explicitly. Every intercepted routine has a recorded reason. `--record build/native-timing.json` retains the generated inputs, states and dependency list in ignored scratch space.

The C++ clock consumes unsigned launcher counter readings without blocking the host event loop. It preserves counter and accumulated-word wrapping, the two-tick minimum, Military Spec's four-tick cap and the general eighteen-tick cap. Realistic takes an additional counter reading even when the first polling loop has already accumulated four ticks. The four `MODEL` indices select native codes Arcade=0, Simple=2, Realistic=6 and Military Spec=1; configuration index and runtime code are separate concepts.

The native frame filter starts at 4.0, weights its preceding float by three and the new interval by one, and rounds at the float store. Its physics timestep multiplies unaccelerated ticks by the exact value of the original `0.02f` constant. Time warp multiplies world elapsed by five after those calculations, subject to the original inhibition word. It must not be implemented by multiplying every subsystem's timestep uniformly. The x87 control word is currently a controlled `0x037f`; a complete DOS startup capture remains necessary before generalising numerical conclusions to the flight equations.

`tfx_replay` is a developer target, built with the tests. It consumes an initial counter followed by frames containing the `MODEL` index, warp/inhibition inputs and timer readings. It reports exact stored numerical bits, animation eligibility/remainder and projectile substeps. Scenery uses the preceding frame's elapsed word, seeded with five at session entry. The native projectile wrapper calls motion then contacts for each chunk of at most ten; even a zero interval performs one pass and the wrapper restores the original elapsed word afterwards.

The reference check executes the original clock, animation gate and projectile wrapper. The launcher counter source is supplied, and projectile motion/contact callbacks are intercepted to record their order and intervals. Aircraft physics, contact outcomes and full session initialisation are **not** claimed by these comparisons.

## Player attitude and Arcade flight

```sh
python3 tools/check_attitude.py --build build --data-dir /path/to/TFX
python3 tools/check_arcade.py --build build --data-dir /path/to/TFX
```

The player's Q15 basis, local rotations, sequential cross-product normalisation and quantised angle extraction follow the native routines. Comparisons cover 4,132 directions, 6,144 rotations, 2,048 normalisations and 2,048 angle extractions. The original atan thresholds are irregular; regenerating a mathematical tangent table changes the resulting angles. World-axis turns transpose the basis before/after local rotation.

The native Arcade path (`0x8dc50`) now supplies aircraft-specific thrust/speed envelopes, afterburner, fuel consumption, filtered control deltas, stall recovery, coordinated turns, motion, gear contact and ceiling limits. One world unit represents eight feet. The numerical translation retains float/double storage boundaries and extended intermediates; it currently requires a host `long double` with a 64-bit significand, as the stores calculation does.

The verifier runs the complete original player initialiser (`0x8c184`, including the aircraft presets) and engine/start setup (`0x8c318`) before multi-step airborne flight. Across all three aircraft, 4,608 steps agree exactly in stored position, integer pose, matrix, control filters, angular remainders, speed limits/response, fuel and angles, including stall/ceiling recovery and afterburner transitions. Host mouse input and scenery/audio/HUD notifications are declared capture boundaries. The FPU control word is the harness's controlled `0x037f`; this is not yet an independent DOS startup capture. The verifier now executes the complete ordinary Arcade player callback (`0x8f56c`) rather than stopping at the inner flight routine. It supplies timer readings and mouse samples, disables automatic recovery explicitly and intercepts warning/audio/scenery output. The automatic recovery controller can select another numerical path even in Arcade mode; it remains separate work. Other flight models, complete collision queries and missions remain unfinished.

`flight.native_arcade_sequences` replays the saved native trajectory hashes without original files or Python. The full comparison tool regenerates and checks all state words; `--save-fixture tests/reference/arcade.txt` updates the compact test fixture only after successful agreement.

## Mission actor populations and surface routes

```sh
python3 tools/check_actors.py --build build --research ../tfx-reverse
python3 tools/check_surface.py --build build --research ../tfx-reverse
```

Compiled programs, commands and entity profiles load from the original archive into typed records. Native initialisation comparisons execute the original dispatcher, profile lookup, pool management, copying and formation placement for all **192 programs / 3,572 individual actors**. Host allocation and SSD creation are declared boundaries. The 50-slot allied/other air pools, single 50-slot surface pool and ten-member group limit follow the executable. Wingmen copy the **preceding member**, so formation offsets accumulate; independently placing every member relative to the leader is incorrect. Actor positions use eight fractional bits and speeds use sixteen. Another 4,096 captures verify wrapped movement, negative-angle table phases and vertical clamps.

The scene owns separate actor assemblies and local animation state, with poses supplied by simulation state. Aircraft/groups execute their route, formation and combat controllers, described below. Surface units execute their native route/controller stacks and update their rendered positions. Their ordering follows the compiled program/native surface pool; `0x75784` visits each once per elapsed AI tick.

Surface comparisons cover all **815 units × 128 ticks = 104,320 updates**, checking every intermediate position, heading, speed, steering/acceleration rate, controller count, wait, stack, cursor and flag via sequence hashes. The supplied context contains no eligible combat targets: nearby weapon selection, scenery-target lookup and radio delivery are declared boundaries. This establishes route/movement behaviour, not firing, damage or live sensor selection. Those requests are explicit outputs from the controller; only radio delivery is currently connected in the windowed integration.

Three compact synthetic-original fixtures add **90,000 updates**, including long travel through a waypoint, acceleration/deceleration, waits, radio and looping branches. `actors.native_surface_sequences` replays those without game files; `check_surface.py --verify-fixture tests/reference/surface.txt` checks their complete inputs and hashes against original execution again. The ordinary scene startup sweep also continues to pass all 128 retail missions with their actor populations present.

## Direct-flight integration limits

The default launch is mission 501. The window now drives player motion through the native timer gate and hands its basis/position to the software camera. It does not render repeated flight frames while waiting for the minimum timer interval. Pause/focus loss discard host mouse deltas and release capture. Keyboard steering is still a provisional adapter to relative native control inputs; it is not yet the complete DOS keyboard/joystick acquisition path.

Live readouts use the original 51-glyph miniature font, read directly from the required reference executable along with its character/advance tables. Their current layout is diagnostic telemetry, not a reconstruction of the complete HUD/MFD layout. Scene inspection remains behind `--inspect`; `--flight-steps` advances simulation for a headless capture.

Gear, engine, air-brake and brake-chute controls are connected for ordinary Arcade flight. The chute state is distinct from engine damage. Ground starts use the native runway/carrier fallback classification. The full damage/death lifecycle, moving-object collision, air combat/projectiles, weapons/sensors, the other numerical flight models, automatic recovery, cockpit/MFDs, campaign/menu/persistence and sound still need integration before this is a complete playable mission.

### Ground-start and takeoff verification

```sh
python3 tools/check_ground_flight.py --build build --data-dir /path/to/TFX
```

Another **9,216 steps** check runway (height 0) and carrier-fallback (height −20) starts, with engines off/on, for all three aircraft. Engine-on sequences are required to finish airborne without a collision. The original initial-placement prologue executes before supplied engine/control changes; landed gear indication comes from the native HUD caller at `0x7e047`. This exposed the original 120-world-unit runway setback, the low-speed-ground-contact flag, the upright-basis landing test, automatic Eurofighter gear retraction and the post-motion contact clamp. A ground start's first placement can reset engine commands, which is why its control boundary must follow that prologue.

Surface height/contact and starting classification are supplied inputs to this comparison. It does **not** verify complete flight sessions with live terrain; terrain queries are checked separately below. Automatic recovery remains disabled in these traces. `flight.native_ground_sequences` replays the saved native state hashes without original files. The runway/gear/contact corrections are shared by headless and interactive flight.

The SSD swept-box primitives (`world/collision`) reproduce the native three projected rectangle tests, including directed tangencies and the original diagonal transform. `tools/check_collision.py --data-dir PATH` compares 11,250 normal, reversed, diagonal and boundary cases against 2.05; the small boundary regressions also run through CTest. The scene now also implements the static terrain dispatcher, checked separately below.


## Stateful scenery and terrain collision

`world/instance` owns mutable parts, custom words, animation cursors, damage flags and object health separately from shared immutable definitions. It executes the authored entry points, conditional branches and helpers. Damage can change models and draw assemblies, start effects, and replace running parameter streams. Stream-triggered events resume the current selector in the same animation tick. Original health comparisons, wrapped subtraction and already-destroyed stream suppression are retained.

```sh
python3 tools/check_instances.py --research ../tfx-reverse
python3 tools/check_world_collision.py --research ../tfx-reverse
```

With Unicorn installed, these compare **19,589 persistent states across all 703 definitions**, then **4,800 complete native terrain queries** across Yugoslavia, Colombia, Libya and Somalia. The latter execute the original cell selection, negative-remainder wrapping, quarter-turn conversion and collision entry, including map seams. Host model handles, draw submissions, collision callbacks and anchor-distance inputs are declared boundaries in the instance test. The world test supplies independently initialised instance resources and records solid contacts; it does not execute damage to the querying aircraft. CTest also covers independent instances, strict-negative damage thresholds, restoration and an animation event that replaces its own stream.

Interactive flight now uses live terrain/building queries and carries the resulting runway surface into the next physics step, following native update order. A solid contact currently stops flight with the diagnostic collision state. Moving-object contacts, full aircraft damage/death and restart, attached-object event resolution, visibility/update eligibility and complete-session comparison remain unfinished. Static instances are still created on first use. Authored point-light/offset requests are retained for their consumers; projected ground-shadow submissions are distinguished from normal model draws and await the shadow renderer. This is not a claim that the whole SSD/render lifecycle is complete.


## Live mission timeline

`missions/timeline` retains the unsigned mission clock independently of the authored time of day. Native messages run at the start of the frame with an inclusive deadline; scheduled SSD events run after rendering and clock advancement with a strict deadline. Both retain authored order and execute once. Off-screen terrain cells named by SETBOB are prepared before flight so their mutable state does not depend on visibility. Message drawing currently uses the diagnostic HUD text adapter; native message layout/lifetime and attached-object resolution remain separate work.

```sh
python3 tools/check_timeline.py --data-dir /path/to/TFX
```

The original `0x71b40` and `0x70e44` agree across **4,096 frame boundaries**, including equality, unsorted event times, zero steps, signed-looking authored times and unsigned wrapping. Message display, SSD dispatch and player SSD refresh are declared capture boundaries; full SSD entry execution is verified separately above. The compact original-result fixture also runs in CTest without game files.


## Airborne controller arithmetic

`actors/air_motion` supplies typed aircraft performance, pitch/turn/speed commands, altitude capture, controller-step shortening and bank-coupled Q8 motion. It preserves wrapped angle/product arithmetic and emits typed afterburner SSD events on display-state edges. Other flight models can use the original six-class turn-envelope data read from the external executable; Arcade retains its profile/speed rule.

```sh
python3 tools/check_air_motion.py --research ../tfx-reverse
```

**9,216 native cases across all 29 aircraft profiles**, plus **576 test-authored cases**, agree for the native controller primitives, envelope selection and motion step. CTest replays the latter without original assets. The afterburner event callback is a declared capture boundary. These checks establish the numerical controller foundation; the waypoint and formation dispatcher is now connected to the live scene as described below; combat acquisition and manoeuvres remain separate work.


## Airborne waypoint runtime

`actors/air` owns mutable compiled programs once per record and keeps each aircraft's cursor, action stack, control state, formation relationship and burst state separately. Group members share command mutations, so a radio instruction delivers once for the group. Aircraft now move in the live game, including waypoint branching, formation catch-up, altitude/speed commands, ground waits, takeoffs and afterburner animation events. Native ground-attack commands produce explicit projectile requests; actual projectile effects and air-to-air acquisition are still unconnected.

```sh
python3 tools/check_air.py --research ../tfx-reverse --ticks 128
python3 tools/check_air.py --research ../tfx-reverse --ticks 512 --intact 1
```

All **192 programs** agree for **352,896 aircraft ticks** with unavailable ground targets and **1,411,584 ticks** with supplied intact targets. Both captures explicitly disable air-to-air acquisition and record scenery, radio and projectile requests without executing their downstream effects. Native allocation/SSD loading and ground-target lookup are declared host boundaries. Four compact, test-authored fixtures cover another **72,512 aircraft ticks**, including shared radio state, waiting/takeoff, extended formation movement, repeated attack bursts and cross-record profile reads. CTest replays these without original files. All 128 retail missions also run 512 integration steps and render their resulting scenes under ASan/UBSan.

The sweep exposed an original 2.05 data mismatch: aircraft groups in missions **721 and 923** (and five retained environment programs) reference the **DESTROYER surface profile**, at 30,000 feet and 500 knots. The native loader stores profiles contiguously, so its air controller reads into the following MISSBOAT record. The reconstruction retains a bounded copy of the relevant adjacent bytes and preserves native first-match clamp order, including inverted limits, without performing an out-of-bounds C++ read. This retains the reference executable’s observable behaviour.

The remaining air integration includes target acquisition, combat manoeuvres/CBN execution, actual projectile creation, incoming-threat responses, aircraft/world contacts and the complete damage/retirement lifecycle. The route comparison does not establish those behaviours or complete combat sessions. The live random stream continues from terrain variant selection, but full original-session random consumption is still a separate verification task.

## Air combat controllers and projectile motion

The live aircraft runtime now acquires opposing aircraft and the player, pursues, uses gun/missile release rules, turns away during its firing cooldown, and runs the original CBN manoeuvre programs. `CBN.DIR` supplies bank order; a resource's archive order is not substituted. Each aircraft owns its scan cursor, target identity, action stack, missile count, manoeuvre cursor and cooldown. Native acquisition scans six of fifty opposing slots at a time. F-117 player detection uses one eighth of the profile range and includes vertical separation; ordinary detection uses horizontal Chebyshev distance.

```sh
python3 tools/check_air.py --combat --ticks 1024
python3 tools/check_air.py --combat --synthetic --save-fixture tests/reference/air_combat.txt
python3 tools/check_projectiles.py --save-fixture tests/reference/projectile.txt
```

The combat comparison covers all **192 programs / 2,823,168 aircraft updates**, with a supplied stationary player near each program's first aircraft group. It checks every intermediate pose, controller state, scan/shot counter, target identity, CBN cursor, shared program byte and emitted request. Twelve independent test-authored scenarios add **98,304 updates**, including incoming threats, disabled weapons, stealth, CBN alignment/completion, countermeasures and firing cooldowns. The saved scenarios run through CTest without game assets or Python. Projectile effects and SSD calls are recorded boundaries in these comparisons; target damage/death is not simulated by them.

All 27 weapon definitions and their timed stage programs now load from the reference executable. Typed C++ projectile motion reproduces attachment/release, gravity, acceleration, guidance, range exhaustion, decoy diversion, low-altitude cruise and child dispensers. Native comparisons cover **108 retail sequences / 27,648 updates**, plus **96 test-authored sequences / 24,576 updates**. Inputs include timer intervals, target coordinates, mounted-store anchors and player ECM state; visual resets and child releases are captured. The original seam-crossing guidance error arithmetic is preserved rather than replaced by an idealised shortest-angle turn. The synthetic trajectory fixtures are asset-free.

Aircraft now react to the live player and launch real projectiles. The integration binds swept contacts to aircraft, surface actors, the player SSD and terrain; weapon effects use the original shared fired/secondary SSD instances. Aircraft whose SSD becomes destroyed enter the original fatal-hit controller. The player SSD can receive hits, but its reports are not yet joined to the complete player flight-damage/death machinery. Scoring, FINISH execution, player weapons/sensors and the ground-unit firing controller remain separate work. The runtime still needs the complete native startup/session random-consumption order and visibility-dependent SSD animation rules.

### Projectile populations, mutual damage and aircraft retirement

```sh
python3 tools/check_contact_damage.py --save-fixture tests/reference/contact.txt
python3 tools/check_projectile_runtime.py
python3 tools/check_air.py --combat --damage-tick 16 --ticks 1024
python3 tools/check_air.py --combat --synthetic --damage-tick 16 --save-fixture tests/reference/air_death.txt
```

The original pool has **98 projectile records**, plus two list sentinels. New shots go at the head and a full pool recycles its oldest record. The C++ pool retains stable record addresses and saves the next link before invoking motion, matching the original even when a dispenser recycles the record currently executing. Child construction runs synchronously; the stage program is re-read from the current record after possible reuse. Copying/moving the pool is disabled because its internal links depend on stable ownership.

The complete original population loop, constructors, removal and substep wrapper agree across **2,576 frames** at elapsed intervals 0, 1, 4, 10, 18 and 55. These cases include all 27 weapons, dispenser pressure at the original pool capacity, both countermeasure kinds, guidance transfer to moving decoys, decoy expiry, reset/registration order and contact-pass traversal. SSD rendering, actual world contacts, mounted-store anchors and aircraft threat registration are explicit boundaries in this population comparison. Contact arithmetic is checked separately; these are not complete mission traces.

The original contact callback reduces the querying projectile's health as well as the victim's custom health. Its signed-zero threshold differs from SSD scripts that branch only when custom health becomes negative. **2,048 test-authored mutual-contact updates** match the complete original VM/callback interaction, including zero contact cost (charged as one), negative thresholds and word wrap. CTest replays the saved asset-free cases.

Fatal aircraft transitions, ejection/falling, impacts and retirement match all **192 aircraft programs / 2,823,168 updates** after an externally supplied fatal hit. Twelve additional test-authored death scenarios add **98,304 updates** and run without game assets. These comparisons supply ordinary ground-impact effects and capture SSD/sound outputs; they do not establish scoring or collision causation. Aircraft/crashed-body visibility follows the original action state rather than waiting for every retired flag.

Native gun stages at `0xa422c` and `0xa42bc` have identical motion but different eligibility in the contact pass. They remain distinct typed stages. Weapon filenames also follow the original loader: the display label is separate, and flying SSD names are prefixed with `x` and truncated to eight characters.

AI request delivery is synchronous: a newly launched missile can become an incoming threat before the next aircraft is updated in the same tick. Chaff/flare diversion clears the previous threat association immediately and points guidance at the decoy's current position. Decoy expiry changes diverted missiles to the native coasting callback with its 30,000-tick lifetime. The live aircraft and projectile systems share one gameplay random stream; procedural vertex jitter remains separate.

All **128 retail missions** run 1,024 integrated four-tick steps and render under AddressSanitizer/UndefinedBehaviorSanitizer with live aircraft weapon releases and contacts. This is a robustness sweep, not a claim that every mission or end condition has been completed. Explosion/impact effect spawning, complete player damage, mounted-store release geometry, player weapon input, flak/surface targeting and the mission-result bridge still need integration.
