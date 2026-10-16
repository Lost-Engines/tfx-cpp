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
* All 128 retail FINISH programs agree with original execution across 8,192 supplied result states: scoring, signed-word conditions, target flags, branch/return handling and campaign statistics. Live combat/mission integration is described below; persistent campaign/front-end execution remains outstanding.
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

All **128 retail missions** run 1,024 integrated four-tick steps and render under AddressSanitizer/UndefinedBehaviorSanitizer with live aircraft weapon releases and contacts. This is a robustness sweep, not a claim that every mission or end condition has been completed. Explosion/impact effect spawning, complete player death/results presentation, ground/designator targeting, flak/surface targeting and the mission-result bridge still need integration.

### Player cannon and mounting geometry

```sh
python3 tools/check_anchors.py --save-fixture tests/reference/anchor.txt
python3 tools/check_cannon.py --save-fixture tests/reference/cannon.txt
python3 tools/check_window_controls.py --data-dir /path/to/TFX
```

Space now follows the original keyboard cannon branch (`0x86898` → `0xa2fdc`), with the F-117 exclusion, landed/death/inhibition checks, the original FLP/COM availability checks, finite ammunition and alternating muzzle. The original starts at **1,760 rounds** and debits ten per visible projectile, including when fewer than ten remain. An unavailable FLP slot consumes a gameplay random value even without a shot; failed/intermittent nonzero bytes retain the native branch behaviour. Host keyboard polling drives this branch once per accepted flight frame, after player physics and before the other actors update; separate mouse-trigger acquisition remains unfinished. The Space-edge carried-store path is now connected as described below.

Native keyboard comparisons cover **4,096 original-mount cases** and **1,024 cases with test-authored mounts**, including negative/low ammunition, both barrels, every eligibility flag, wrapped coordinates and random-state effects. Cannon audio is a declared output boundary; the absent optional external-device callback executes normally. The synthetic cases run through CTest without game files. An isolated virtual X11 check additionally verifies actual Space input changes the live ammunition HUD and Escape exits.

Cannon and store mounts load from the original executable for all three aircraft. The complete native anchor transform agrees in **4,096 cases** (512 saved asset-free cases). Each signed high-word product is rounded separately before wrapped accumulation; replacing it with a conventional matrix dot product changes the result. Mounted-store attachment in live projectile motion now uses this geometry.

The original projectile constructor only updates its retained mount byte when the release angles match the current player angles. Untargeted releases also share one mutable aim point; every subsequent such release can change it. The population comparison now includes both details and totals **3,220 frames** at the native 98-slot capacity. Native substep elapsed values are used during child births; outside the update, releases see the caller's current elapsed word.

### Carried armament and air-to-air acquisition

```sh
python3 tools/check_loadout.py --save-fixture tests/reference/loadout.txt
python3 tools/check_sensors.py --save-fixture tests/reference/sensors.txt
```

Default loadout pairs, aircraft-specific mounting anchors and the pylon successor ring come from the selected original executable. The two native selection routines have different purposes: `0x8b9c4` skips another pylon of the current weapon type when cycling manually; `0x8bba0` advances to another usable store after release. The cannon is a separate sentinel in this ring, skipped by the F-117. The release primitive (`0x8bd8c`) retains byte-count wrap, the JP233 empty-pylon visual exception and Arcade/simulator unlimited-store configuration. Projectile construction runs before consumption/selection, so attachment observes the original launch pylon.

**6,192 original-code comparisons** cover all 30 defined retail fits, 18 test-authored fits, both selectors, empty slots, all 27 weapons, inhibition/unlimited states, wrapped coordinates, mount transforms and target-clear side effects. Empty slots use byte 255; the original selector reads two metadata fields beyond its 27-record table even for these slots. The C++ reader owns those two bytes explicitly rather than indexing outside the weapon vector. The synthetic cases are replayed by CTest without game assets.

Radar acquisition (`0x836ac`, `0x8296c`, `0x828b0`) preserves 20 contact slots across scans and fills holes with new contacts in original pool/enumeration order. Its 50-mile cutoff uses the original integer division and word operations. The air-to-air seeker (`0x93328`) preserves rear-aspect/cone/range/side tests, separate selected/tracked/guidance contacts, moving Q8 screen reticle and lock timers. Angular differences deliberately retain the original wide signed subtraction at the angle seam.

**1,024 persistent radar frames and 4,096 acquisition/lock states** agree with original execution. Screen projection and sound/radio output are supplied boundaries in this comparison; it does not prove the graphics projection or the separate laser, anti-radiation, cruise and anti-ship controllers. Native contact-buffer overflow beyond the supported 20 slots is not reproduced as memory corruption.

The live build connects Enter, Backspace/O, F, C and Space to selection, target cycling, cannon and finite carried-store release. The private X11 smoke test verifies both the store count and cannon ammunition change through actual keyboard input. All 128 retail missions initialise their default loadout, run 1,024 four-tick integration steps and render under AddressSanitizer/UndefinedBehaviorSanitizer. Complete cockpit radar drawing, ground/designator acquisition, separate mouse-trigger handling and missile-lock audio remain outstanding.

### Player system damage and disabled flight

```sh
python3 tools/check_damage.py --save-fixture tests/reference/damage.txt
python3 tools/check_disabled.py --save-fixture tests/reference/disabled.txt
```

The SSD percentage-damage opcode delivers its callback synchronously, before testing the fatal branch. This matters when the callback changes that SSD's state or animation. Player reports now execute entry 13 and the native system-damage calculation (`0x8f460`/`0x8f3ec`) on the same gameplay generator used by aircraft and projectiles. Solid contacts also debit the querying player's health and deliver the native 100-percent report. A regression exercises a re-entrant restoration callback before the fatal decision.

The native calculation samples eleven system slots in its authored order, even for repeated/zero reports. It distinguishes intermittent faults (14), failed systems (11), normal/active states and invulnerability. Intermittent faults clear strictly after 1,080 ticks in `0x871d4`; the word repair clock retains wrap/signed comparisons. **8,192 cases** agree in all system bytes, clocks, random state, stored damage double and notification count. The later cockpit work below establishes the slot names from the actual HUD label table and manual.

A lost player now enters the translated disabled/ejected flight branch (`0x8e5a8`) rather than staying flyable or freezing in mid-air. It retains automatic levelling, the special Mach 0.5 request, roll, matrix normalisation cadence, descent, supplied ground contacts and integer/float handoff. **4,608 complete callback steps** match original execution across the three aircraft, beginning with 64 ordinary flight frames before entering the disabled state. These sequence cases run through CTest without original assets. This establishes the motion branch, not the complete ejection camera, crash-effects lifetime or front-end result sequence; those remain to be joined.

Weapon-system faults participate in Space-edge store release, while the separate held-key cannon branch retains its original nonzero-byte checks. Engine display states are refreshed from the engine fields at the original frame boundary. The Arcade model's original handling is retained; physical-model damage effects and complete cockpit fault displays are still outstanding.

After joining these paths, all 128 retail missions again run 1,024 integrated four-tick steps under AddressSanitizer/UndefinedBehaviorSanitizer. All 24 CTests pass in normal, sanitizer and Release builds; private-window weapon input also passes. These are bounded subsystem/robustness checks, not completed-mission or end-to-end campaign proofs.

### Live mission outcomes and actor surfaces

```sh
python3 tools/check_progress.py --save-fixture tests/reference/progress.txt
python3 tools/check_credit.py --save-fixture tests/reference/credit.txt
python3 tools/check_death.py --save-fixture tests/reference/death.txt
python3 tools/check_world_contacts.py --save-fixture tests/reference/world_contacts.txt
```

The live session now drives authored target destruction/credit, all six completion kinds, protection failure, per-target timers, return-to-base scoring and delayed termination. Airborne starts use the native completion delay; landed starts require stopping after return. Timer comparisons preserve their strict boundaries, signed/unsigned distinctions and word wrap. The return-to-base award belongs to the parser's score variable, separately from the combat score passed to FINISH. **4,439 original-code frames across 512 supplied-outcome sequences** verify this rule/termination layer.

Aircraft and mobile losses now supply native type-filtered mission counts and combat credit. The player's kill acknowledgement consumes a random value before the fatal-aircraft routine chooses ejection/falling. Native quirks remain: some mobile/air credit is independent of the shot owner. **4,096 controlled native credit cases** cover ownership, permission, type filters, signed score wrap and violations. `setidnum` and `setmobileid` are named aircraft/surface type filters in C++, following their actual consumers rather than assuming the first only concerns static scenery.

Player loss and impact remain separate stages. **4,096 native transition cases** verify outcome/status codes and the strict 200-tick post-impact countdown, including repeated loss and invulnerability. The live FINISH handoff occurs once per terminated flight, using fresh direct-entry pilot statistics. A simple result display shows the resulting score/mission value until the original front-end graph and pilot persistence are connected. This is not a replacement campaign UI or a proof of a completed normal mission.

Player surface queries now include nearby mobile SSD assemblies, including carrier decks, after the terrain query. The native broad-phase box has a minimum radius of 1,024 world units and excludes its exact edges; **8,192 original region/eligibility cases** match, including word/dword wrap. Without this bridge, carrier starts lost their deck contact and eventually crashed while parked. These starts now remain on their actual deck. Surface flags use the native byte representation, distinct from aircraft word flags; hostile/dead/retired handling now follows that byte.

Compiled type-17 fixed placements also load, preserve authored initial events and traverse in the native reverse order. None is present in the 192 audited reference programs; **1,408 test-authored placements** verify the retained loader/list path against original execution. Surface heights remain the authored absolute word, rather than adding the actor's visual Y translation.

The private X11 input check additionally reaches a result through the live mission 605 combat path, verifies the result image stays stable after termination and closes it with Enter. Ground/designator targeting, complete permissions/court-martial handling, water/aftermath crash effects, moving-deck velocity transfer, the refuelling-aircraft collision path and original front-end result artwork remain outstanding. Direct launches currently use Arcade scoring eligibility; persistent game-mode configuration belongs to the pending front end.

All 28 CTests pass in normal, Release and sanitizer builds. All 128 retail missions again run 1,024 integrated four-tick steps under ASan/UBSan; the sweep checks that any reached FINISH handoff occurs exactly once. Mission 605 reaches its loss/result path naturally in this bounded run. Carrier-start mission 504 remains parked after the actor-surface fix. Full original/C++ mission traces remain a separate verification gate.

### Ground designation and weapon targeting

```sh
python3 tools/check_ground_sensors.py --save-fixture tests/reference/ground_sensors.txt
python3 tools/check_damage_centres.py
python3 tools/check_projectile_runtime.py
python3 tools/check_window_controls.py --data-dir /path/to/TFX
```

The live ground view uses the original unlocked gimbal/intersection (`0x92c24`, `0x93040`) and locked following camera (`0x92a34`). The F-117's relative gimbal limits, signed-word intersection radius, frame-based keyboard steps, ten zoom levels and different search/follow camera strides remain distinct. Z enters the designator and designates a point; arrows aim, comma/period zoom, X clears acquisition and F1 returns to the aircraft view. This is the retail 2.05 Z binding; the earlier manual's Y description differs. Display overlays/projection are still diagnostic rather than a complete original HUD.

Anti-radiation C selection (`0x7c828`) cycles live radar-emitter types and captures their current position. Harpoon's first Space press selects the nearest eligible ship (`0x7cb5c`, `0x9323c`); the next releases it with a live actor reference. Ship-type eligibility loads from the selected original executable. Laser-guided stores use the shared mutable designation point, rather than freezing a separate copy for every missile. Selecting a later point can therefore change guidance for an earlier release, as in the original.

Maverick selection (`0x7ca24`) searches eligible mobile damage zones near the designated point, preserving slot/zone ordering, strict range/tie comparisons and native wrapped squared distances. Its tracking point deliberately ignores actor heading and anchor height (`0x7c998`). The zone centres come from leading damage-once/staged boxes in SSD collision entry 2 (`0xb7b90`), separate from the visual model anchors. All **703 original SSD definitions / 698 targetable boxes** agree with native enumeration at the moving-instance orientation zero.

Original-code comparisons cover **8,192 unlocked designator/intersection states, 2,048 locked camera states, 4,096 wrapped distance estimates and 4,096 surface selections**. Mobile tests supply separately verified SSD centres; camera cases stop at the graphics boundary. A compact one-in-eight subset of synthetic inputs is replayed by CTest without game data. Projectile population checks now cover **3,864 frames**, including a moving shared designation, constructors, dispenser births, recycling and decoys. The private X11 check additionally selects a ground weapon, opens/zooms/aims/locks the designator and releases a store through real keyboard input.

Complete ground HUD/MFD artwork, target-planner interaction, cruise target programming, separate mouse-trigger handling and end-to-end native targeting-session traces remain outstanding. The current aircraft-view projection is still a supplied boundary in subsystem comparisons; matching acquisition arithmetic is not a claim of pixel-identical HUD output.

### Surface-unit combat

```sh
python3 tools/check_surface_combat.py --save-fixture tests/reference/surface_combat.txt
```

Mobile surface units now execute their nearby-aircraft firing requests (`0x7be44`) and authored ground-attack requests (`0x7bee8`) through the live projectile system. Enemy/neutral units consider the player first, then scan the allied aircraft pool backwards; allied units scan the enemy pool. The original retains different player/nonplayer range boundaries, F-117 detection reduction, per-unit player shot count, one-in-sixty random firing check, minimum launch speed and vertical anti-air launch angle. Ground attacks use their separate authored launch pitch and only fire at an existing intact terrain assembly.

Surface route requests now deliver synchronously before movement. Returning requests and consuming them afterwards would launch from the next position. The native comparison includes **512 complete route sequences**, alongside isolated acquisition/ground-attack cases, for **4,096 scenarios / 135,492 updates / 1,759 weapon constructor requests**. Original enumerators, bearing calculations, route/controller/movement code and random calls execute; terrain presence/destruction and the projectile constructor are explicit boundaries. A compact subset of synthetic cases runs through CTest without game data. These checks establish surface-unit firing, not the separate mission-area flak controller or a completed ground-attack mission.

### Native presentation media

```sh
python3 tools/check_media.py
python3 tools/check_media.py --build build-san
```

The C++ media library now decodes original `war ` screen images, four-plane sprites and the word-bit compressed delta animations (`0xde8cc`) directly from external archive resources. It keeps indexed pixels and the original palette, validates each delta run within its VGA plane and can retain the preceding screen as a delta background. Stored animation blocks and the declared playback frame count remain separate: three original resources contain extra stored blocks, whose playback meaning must be handled by the presentation caller rather than guessed by the decoder.

All **116 indexed screens, 39 sprite resources and 40 animations / 1,606 compressed blocks** compare byte for byte with independent extraction. Every animation block also executes in the original x86 decoder before final composed pixels and written coverage are compared. The complete corpus passes with ASan/UBSan, alongside synthetic literal-refill, retained-background and malformed-stream tests. No game artwork or original instructions are bundled. This establishes the media layer; original presentation scheduling, fades, fonts, menus and campaign dispatch are still being connected.

### Presentation graph decoding and control flow

```sh
python3 tools/check_presentations.py
```

All nine retail saved parser graphs now decode into typed clip/text, branch, assignment, audio, planner, menu and launch records. Editor linked-list/pointer bytes are discarded; destination ordinals and resource strings retain their actual data meaning. CP437 text is bounded by its saved length, which excludes a terminator in the retail files. Unsupported retained node families are preserved as opaque data rather than interpreted as a guessed action.

Every decoded semantic field, including offsets, text settings and native audio modes, matches independent extraction. The original numeric handlers agree for all **254 retail branch records and 163 assignments / 991 supplied-state cases**, including native gosub/return state and 32-bit wrap. This is the retail subset of the research corpus; the demo's additional 17-byte text layout is not silently accepted as retail.

The C++ control-flow runtime executes assignments, conditional/unconditional branches and subroutine returns until an explicit media/menu/session action is ready for its host. Synthetic tests cover wrapping arithmetic, return to the statement after a call, suspension/resumption and every truncated prefix of a test graph. Reconstruction safety limits reject non-yielding control flow and excessive calls instead of reproducing out-of-bounds memory access. This is not yet a claim of complete original front-end, pilot persistence or campaign-session execution; those host consumers remain in progress.

### Original presentation fonts

```sh
python3 tools/check_fonts.py
python3 tools/check_fonts.py --build build-san
```

All ten presentation fonts now load their original bitmap tables from external `TFX.DAT`. The two fixed fonts use code-object lookup rows; proportional fonts use their width, glyph-pointer and bitmap tables. No captured glyph images are bundled. The immutable executable asset tables own the decoded bank for presentation consumers.

**1,104 glyphs and 132 complete-string cases** match fresh original VGA execution in every pixel, written coverage, native width word and line height. Cases include black ink, all horizontal phases of the fixed-font string renderer, all four clipped corners for proportional styles and empty-string metrics. Native measurement and drawing stay separate: case handling, final spacing and the small font's extended-glyph advance differ. The fixed eight-pixel renderer also narrows a following uppercase I, while its width calculation remains fixed. Null original title-font pointers remain explicitly unavailable rather than borrowing another font.

The comparisons render complete VGA frames rather than relying on cropped glyph snapshots; a glyph can draw beyond the width reported by its measurement helper. Asset-free tests exercise owned table data, black coverage/transparent holes, extended baselines, distinct measurement/drawing advances and fixed-font termination. This establishes character/string rendering; briefing substitution, full text layout/reveal and presentation playback are the next consumers.

### Complete briefing text and reveal

```sh
python3 tools/check_text.py
python3 tools/check_text_clock.py --save-fixture tests/reference/text_clock.txt
```

Text preparation (`0xb1714`, `0xb14dc`) now handles original line breaks, ASCII uppercasing, named substitutions, signed numeric formatting and `^briefNNN.txt` language-file replacement. Substitution occurs after literal uppercasing, so inserted pilot strings retain their own case. Line widths, left/right/centred positions, line heights, shadows and visible prefixes follow the native routines. A bare CR retains its original two-byte skip. All shipped captions and language files fit the original twenty 80-byte line buffers; oversized/cyclic custom input receives a bounded error instead of overwriting neighbouring state.

**435 complete text cases and 123 revealed-prefix cases** match original preparation and VGA composition in every line, coordinate, count, pixel and written-coverage bit. These include **275 external references across all five languages**. The native file-loading boundary receives actual independently extracted language bytes; C++ reads those same assets directly from the archive. Static and partial drawing execute unchanged in the original, including whole-line shadow-before-foreground ordering.

Reveal timing (`0xb1b28`, `0xb1268`, `0xb1c16`) retains the fast counter's signed low-word delta, per-frame increment clamp of 1–50, two ticks per character, fractional remainder and Space consumption. **2,048 sequences / 131,072 native transitions** agree, including low-word/full counter wrap and completed/empty captions. Compact synthetic cases are replayed by CTest without game data. The input counter and the following VGA draw are explicit boundaries in that arithmetic comparison; the separate prefix comparisons establish the resulting drawn text. Full scene wait/fade/animation scheduling remains the next integration step.

All 35 CTests pass in normal, Release and sanitizer builds. The complete multilingual/prefix comparison also passes with ASan/UBSan. Font and text checks share a small declared planar VGA write-capture helper; it does not emulate the rest of the original game or hardware.

### Presentation timing and fades

```sh
python3 tools/check_presentation_timing.py --save-fixture tests/reference/presentation_timing.txt
```

Scene input (`0xb1128`), wait countdowns, animation playback (`0xc9fac`) and six-bit DAC fades now have native comparisons: **4,096 input cases, 4,096 countdown decisions, 65,536 animation updates and 240 complete palette uploads**. Compact synthetic cases run through CTest without game assets. Images hold their wait timer while text is revealing; animations do not, and text-only waits test the previous count rather than the decremented value. Space finishes an incomplete caption before advancing; mouse-button priority, Escape sequence skipping and Shift+Q retain their native ordering.

Animation clocks advance at most one block per callback and discard accumulated backlog. The initial frame plays once; repetitions resume at the second stored block over the retained final pixels. Declared frame count controls playback even when additional blocks are stored. Palette ramps scale the original six-bit DAC entries before display expansion, preserving integer rounding. These verified kernels are being connected to the native scene host; complete front-end execution remains outstanding.

### Integrated scene playback

```sh
python3 tools/check_scene_player.py
./build-san/player_probe --corpus /path/to/TFX
python3 tools/check_presentation_window.py --data-dir /path/to/TFX
./build/tfx --data-dir /path/to/TFX --presentation cdintro
```

The scene player joins media, text, input, countdowns and DAC ramps. The graph session retains nested-parser return positions, numeric state, sequence skipping and per-node key/reveal resets. Text-only scenes retain their pre-fade reveal clock; image/movie captions begin after their fade. Static captions compose before fade-in, and animation repetitions retain the previous pixels while resuming from block two. All ten font styles remain indexed software drawing. The retained text-only palette selector distinguishes the embedded palette from the caller's logical palette; fade uploads remain separate from logical palette storage.

**193 complete original still/text handlers match across 1,157 composed content frames**, including caption preparation/reveal, Space consumption, Escape termination and the surrounding scene loops. Asset loading, supplied timer samples, display flips/retraces and palette output are declared boundaries; decoding, fades and animation clocks have the separate complete comparisons above. The test reproduces the original parser caller's per-node reveal reset rather than carrying the previous caption count into an isolated handler. This does not establish a complete original front-end session or its inherited palette/clock state.

A sanitizer run completes **592 scene/language cases and 194,404 content/ramp iterations**, covering every one of the 372 retail visual nodes and all five languages for external captions. Those full playback runs establish resource and lifetime coverage, separately from native output agreement. Private X11 tests verify that Space advances one scene while Escape and Shift+Q finish the presentation cleanly. All 37 CTests pass in development, Release and ASan/UBSan builds.

The developer `--presentation NAME[:FUNCTION]` entry runs original graph scenes in the native window; `--frames N --screenshot FILE` provides deterministic headless captures at virtual 70 Hz. Audio actions are explicitly deferred. Menus, pilot persistence, waypoint planning and game launches remain host boundaries; reaching an unfinished host action reports it rather than fabricating campaign progress.

### Original options menus and pointers

```sh
python3 tools/check_menus.py
python3 tools/check_cursors.py
python3 tools/check_presentation_window.py --data-dir /path/to/TFX
./build/tfx --data-dir /path/to/TFX --menu mastopts
```

All eight shipped `.opt` scripts now load directly from the selected archive. Typed choices retain authored click bounds and declaration order, label destinations and numeric assignments. The supported script subset also retains bitmap/animation selection, cursor style and the no-selection-box flag; unsupported custom commands fail explicitly. No retail menu is replaced by a newly authored list.

The original interpreter agrees on **eight menu setups, 43 complete label/assignment paths and 17,104 mouse positions**. Tokenisation, original box registration, label lookup, numeric writes/returns and hit testing execute unchanged; file loading, graphics/pointer output, selection-box drawing and the interactive display loop are declared boundaries. CTest adds asset-free checks of overlapping inclusive bounds, signed dword writes and invalid labels.

Both embedded cursor styles and their active/idle sprites load from `TFX.DAT`. **144 pointer frames match original VGA sprite drawing**, including the four clipped corners, transparent holes and supplied positions. Right-edge clipping preserves the blitter's four-pixel group quirk. This checks pointer pixels independently from menu script semantics; it is not a complete native-menu frame comparison.

The menu host uses original indexed artwork, looping flag animation, palette fades and pointers. It applies a choice on press and waits for release before fading, matching the native `0xd5750` branch sequence. Asset-free tests cover held clicks and single assignment. A private X11 test clicks the FWS box through the corrected 4:3 viewport, checks that holding does not exit early, then releases and verifies the chosen index and clean exit. Pointer coordinates share the same fitted rectangle as final display, including framebuffer/window scale differences.

Options nodes now suspend/resume the graph session through this host. Direct developer `--menu NAME` launches allow checking individual scripts before pilot and mission dispatch are complete. Full original pilot/save/load/planner flow remains outstanding; this work does not fabricate those state transitions.

### Native pilot-save storage

```sh
python3 tools/check_saves.py
```

The save codec follows original writers/readers `0xb3aa8` and `0xb3c14`. Files contain **thirty fixed-order variable slots**, including three reserved numeric slots beyond the 27 declarations in retail `tfx.par`. Text occupies 21 bytes; numeric slots store complete little-endian dwords. A word return-stack depth precedes function/statement word pairs and the final resume pair. Return entries name the original call statements; native return processing advances past those sites. A function word of `0xffff` means there is no saved resume position.

**512 original write/read states agree** across all four writer modes: no resume, previous statement, current statement and following statement. Cases include reserved-slot bits, signed numeric bit patterns, empty/maximal strings and up to five saved calls. All four existing DOS saves in the reference install decode and re-encode with only bytes after string terminators cleared. No installation file is modified by the checks. New files initialise that padding instead of copying DOS's stale memory.

Asset-free tests cover complete round trips, every truncated prefix, trailing bytes, string limits and invalid saved graph positions. Loading rejects a stack beyond the original 100-entry storage and out-of-program positions rather than following arbitrary memory. The graph runtime can now snapshot all four native resume modes and restore saved call sites, values and reserved slots. A nested suspended-action test serializes, reloads and returns to the statement after the original call; the host explicitly completes the load action after restoration. This establishes file compatibility, serialization and runtime restore; pilot-selection UI, autosave timing and complete campaign-session wiring remain separate integration work.


### Pilot enrolment and front-end flight dispatch

```sh
python3 tools/check_pilot_names.py
./build/pilot_probe /path/to/TFX
python3 tools/check_frontend_window.py --data-dir /path/to/TFX
```

Normal startup now follows `tfx.par` through the introduction, enrolment and original main menu. `--skip-intro` enters the authored enrolment statement, preserving subsequent assignments. The front-end owns shared pilot variables and its suspended parser/menu; the existing flight loop is a callable host using the same window. Numeric launches and `%mission` launch the selected mission. On a completed flight, FINISH variables return to the parser; accumulated pilot score is preserved. Direct `--mission` entry remains available. Escape during an unfinished flight still exits the integration build rather than inventing a campaign outcome.

Pilot artwork, embedded arrow, labels, rank/status names and scan-code character table load from the selected original installation. Name editor `0xa1ee0` agrees for **1,155 complete native input sequences**, covering all make codes, eleven-character editing, Backspace, Escape/default names and Control qualification. The final callsign confirmation supplies the Control qualification bit; the original `WAYTXT/A` marker also qualifies new pilots. Edited names remain uppercase, while the twelve-character default surname remains intact. Pilot rows retain original status/rank/name ordering and the inactive-slot replacement/active-pilot overwrite prompts. The inactive-pilot “delete” confirmation marks only the chooser's in-memory entry empty until replacement, as the original does.

Enrolment saves, `slog`, `rlog`, `spos` and completed-training storage now connect to the native save codec. Existing lower-case DOS filenames are reused instead of creating case-only duplicates. Loading restores the saved parser statement and call stack before completing the enrolment/load host action. The new isolated test checks creation, qualification, persistence, load/replacement, native resume positions, completed-training markers and authored 501-to-502 training progression with a **supplied flight-result boundary**. That supplied result is a parser integration check, not proof of completing those engagements through combat.

The private X11 check uses a temporary installation containing links only to `DID.DAT` and `TFX.DAT`. It types names, qualifies/saves a pilot, chooses training, skips its briefings, enters live mission 501, exits, then reloads the pilot and enters again. It never modifies the reference installation or sends desktop input. Existing private flight weapon/targeting/results checks still pass. Development and Release builds pass all 39 CTests; the pilot integration check also passes in Release and ASan/UBSan. Full original enrolment-frame comparison, planner/loadout, high-score consumers and complete flight/campaign-session equivalence remain separate work.


### Original high scores and Arcade return

```sh
python3 tools/check_scores.py
python3 tools/check_score_frames.py
```

The original high-score roster, signed ordering, display and `tfx.hs` storage now run through the front-end host. `sscore` displays the table; `vscore` also inserts the current pilot's score, including the authored Arcade menu's view-scores path. Strictly greater scores qualify, so tied entries retain their existing precedence. Missing files use the embedded defaults; failed checksums restore and rewrite them, matching the original loader. Names come from executable tables and current pilot variables; no default roster or captured screen is bundled.

The 670-byte payload contains ten 67-byte records: three 21-byte names and a signed score. Native `0xa69b0`/`0xa6a10` use a privately reset original random sequence for byte XOR and the following checksum contribution. **512 complete encoding/checksum/decoding cases, 512 corrupted files and 1,024 native insertion cases agree**, including signed extremes and ties. New string padding is zeroed rather than copying old buffer contents. Asset-free tests check every corrupted byte, every truncated prefix, trailing data, name bounds and stable ranking.

The complete original high-score handler `0xa6c3c` agrees across **274 VGA frames**: the expanding text clip, exact labels/numbers, font pixels, shadows and all thirty selected-row highlight colours. Background decoding, display pages/retraces, cached palette and final mouse exit are explicit supplied boundaries. Native formatting, clip setup, fonts and screen-loop control run together. The right clip edge is exclusive; the bottom edge is inclusive. The display and highlight retain the original retrace-driven timing.

The isolated pilot/front-end test additionally chooses Arcade, writes its temporary log without a resume position, submits/displays a score, dismisses the table, returns through `rlog` to the main menu and checks repair of a corrupt score file. All files remain in a private temporary directory. Development, Release and ASan/UBSan builds pass 40 CTests and the extended pilot integration test. Planner/loadout and complete campaign-flight-session equivalence remain outstanding.


### Editable planner documents

```sh
python3 tools/check_planning_documents.py
python3 tools/check_planning_documents.py --build build-san
```

The planner's text `.WAY` resources now load into owned route/waypoint structures with retained commands, map/world/palette metadata, mission parameters and original briefing bytes. These are separate from the compiled `.WAY` programs used in flight. The data layer does not yet replace the pending planner host action or provide its interactive map/loadout screen.

Native `0xa7dc0` executes its complete line reader, scanning, path construction and command constructors with a bounded supplied allocator. **180 original loads agree across 8,916 waypoint records**, including all **30 retail Tour of Duty planner sources**. The compared fields are all sixteen resulting parameter words, map/world/palette names, route labels, waypoint ordinals/coordinates and the exact remaining briefing byte range. Source commands are preserved verbatim by C++; their planner compilation/editing semantics are a separate consumer, not claimed by this comparison.

The original header uses fifteen dword `%d` destinations spaced two bytes apart. Following fields overwrite preceding high halves, while a partial header leaves its final high-half write in the next word. The typed parameter loader preserves this effect, including legacy headers that provide only a format tag and retain initial defaults. Fields whose consumers are still unresolved remain explicitly retained. Native coordinate scanning also narrows to signed words; C++ does so without overflowing a waypoint allocation.

Two retained version-1000 Somalia sources, `somal_n.way` and `somal_dc.way`, omit their first route name. They are outside the thirty retail planner actions. The 2.05 reader misinterprets the following lines; `somal_n` reaches a null command-pointer write. C++ rejects these malformed route headers explicitly. The comparison checks those rejections separately from the 180 matching valid loads. Asset-free tests cover preserved commands/briefing bytes, native header overlap/spill, omitted defaults, signed coordinate narrowing and all truncated prefixes before the final route terminator. All 41 CTests pass in development, Release and ASan/UBSan; the full document comparison also passes with the sanitizer-built loader.


### Compiled planner artwork and palettes

```sh
python3 tools/check_planner_panel.py
python3 tools/check_planner_panel.py --build build-san
```

The original planner's frame is an executable-backed painting stream (`0xa9c34`), rather than a separate bitmap. A bounded decoder reads that fixed 2.05 artwork representation from external `TFX.DAT` and produces indexed pixels with explicit written coverage. It accepts only the painter's ink/run, position, repeat and VGA-plane-mask operations; it does not execute original game code or introduce a CPU emulator into the game. No captured image or original painting program is bundled. The coverage mask keeps the map rectangle transparent and distinguishes untouched pixels from written black.

The complete original painter agrees in **all 64,000 pixels and coverage bits**, including the curved frame details and plane-specific writes. The planner palette also agrees for **128 complete native compositions** through `0xab3ac`: map colours remain underneath the 80-entry interface ramp and sixteen marker colours. The interface bank lives beside the painter in the code object; the marker bank is in the data object. C++ reads both original banks as data. The comparison also passes with ASan/UBSan, and the Release/sanitizer planner tests check overlay composition without erasing uncovered map pixels.

These assets are ready for the interactive planner consumer; loading a planner action remains an unfinished host boundary until its route briefing, editing and arming workflow are connected.

### Planner map, annotations and route artwork

```sh
python3 tools/check_widget_font.py
python3 tools/check_planner_maps.py
python3 tools/check_planner_notes.py
python3 tools/check_planner_routes.py
```

The planner now owns its three original map layers, interface palette banks and region labels. Native order is physical relief, AWAC and political. The proportional widget font is separate from the presentation and HUD fonts and loads from the original executable. **416 complete native font cases agree** in width, pixels and written coverage, including every byte code, accents, plane phases, top clamping and the bottom edge. Immutable executable assets are decoded once and shared by their consumers.

**90 complete map pages agree** in every pixel and DAC entry across all thirty retail planner actions and all three map layers. **174 complete annotation windows agree pixel for pixel**, including their original frame, positioning, text limit and text/frame overlap. **177 route pages agree** at every waypoint in the retail briefing reviews, including native line order, numeric labels, edge placement and clipping. These comparisons execute original loaders and complete painters with supplied DOS resource access, bounded heap storage and four separately captured VGA pages. Optional satellite/world 3D setup remains outside these 2D comparisons. No captured artwork or game instructions are bundled with the C++ runtime.

Annotation indexing preserves the original discrepancy between its two number scanners. Blank lines after ESC in mission 829 cause notes 4 and 6 to replace key zero, while their widget headers still load correctly. Text is bounded to the original 400-byte buffer. Unselected native route labels read a header before the route array; the reference supplies zeroed mapped heap guard storage, while C++ expresses the unselected condition without that out-of-array access. Asset-free regressions cover annotation defaults, duplicate replacement, carriage returns and text bounds.

The map/annotation/route painters are currently independent components; interactive planner state, route editing, loadout and flight handoff remain the next consumers rather than being implied by these frame comparisons.

All four new native comparisons pass with development, Release and ASan/UBSan probes. All 41 CTests also pass in those three configurations.

### Live Tour of Duty review and translated notes

```sh
python3 tools/check_planner_segments.py
python3 tools/check_planner_review.py
python3 tools/check_planner_languages.py
./build/pilot_probe /path/to/TFX
python3 tools/check_frontend_window.py --data-dir /path/to/TFX
```

The front-end now handles all thirty retail planner nodes. Their mode is **1**, which calls native `0xaceb4` to review the player route, queues action 2 and returns automatically to the presentation parser. This is distinct from the editable route/mission-authoring modes. There is no invented Enter-to-launch step: Space or held right mouse dismisses each available note, route legs reveal in order, and the authored graph then launches the mission.

The animated line painter uses signed 16.16 DDA sampling and excludes its final endpoint, unlike the completed route's inclusive Bresenham lines. **727 complete native segment captures agree** in every pixel and returned remaining length, including zero, partial, complete and excessive extents. **Thirty complete original reviews agree in 2,004 note/reveal transitions and successful automatic return**. The original controller, note waits, geographic label loading and segment completion logic execute; optional world/satellite setup remains a supplied boundary. The original forty-retrace fade executes too: **1,230 complete displayed palettes agree**, including each ramp stage and the final black screen. These event comparisons complement the separate complete-frame painter comparisons; they do not claim an exact desktop-time/display-flip recording of an entire review.

Translated `.way` files overlay notes by key rather than replacing all English waypoint instructions. **150 live introductory screens match the original pixel for pixel**, covering every retail review in English, French, German, Italian and Spanish. The check also verifies that Enter/Escape do not dismiss the C++ note and Space does. Notes retain their raw blocks until requested, matching native delayed widget decoding. This matters for French mission 829: a stray `3` block is replaced by a later note before it can be displayed. Eager decoding would reject valid gameplay. Asset-free tests cover this replacement and translated overlays retaining other keys.

Pilot integration now follows the original main menu, Tour squadron choice, mission 801's review, its flight-launch boundary, a supplied successful result, and mission 802's review/launch. The supplied result tests campaign continuation independently of combat. All thirty text player routes also agree with their compiled flight waypoint lists. Editable authoring modes and loadout selection remain separate work. The segment/review/language comparisons and pilot integration pass in development, Release and ASan/UBSan; all 41 CTests pass in each configuration. A private X11 test also enters live FWS and Tour flight through the actual Release window, including pilot reload and held-right-button review dismissal.

### Arming permissions and HUD glyphs

```sh
python3 tools/check_arming.py
python3 tools/check_hud_font.py
```

Original weapon records now expose all three aircraft's mounting masks. The typed inventory supports direct assignment/clearing separately from interactive permission checks, as native `0x8b3d4` does. Native `0x89c08` also makes slots 0/7 mutually exclusive with 3/4/8/9 in the F-117 and F-22. This checks model presence, including temporary placement previews, rather than remaining ammunition. Eurofighter uses its masks without those additional exclusions.

**11,624 complete native states agree** across original and synthetic mask tables, all occupied-slot pairs, unrelated stores, emptying a slot and direct assignments that an interactive permission check would reject. Eighty-four compact original oracle cases also run without game assets in CTest. Existing default-fit, pylon-cycling and release checks still agree across **6,192 cases**.

The existing HUD glyph painter agrees with native `0x87154` across **576 complete frames**, including every byte code, black/white ink, all horizontal plane phases, clipping and embedded NUL. The C++ painter now stops at NUL, matching original strings. This font also draws the arming screen's small labels. Native VGA capture permits writes to each page's unused physical padding while retaining only visible pixels; all ninety planner map-page comparisons still pass.

Both new comparisons and all 42 CTests pass in development, Release and ASan/UBSan. These changes provide inventory permissions and glyph rendering for the arming interface; its interactive controller and 3D preview remain in progress.

## Carried-store model attachments

`models::interpret` now executes model opcode 81 against a supplied, borrowed table of carried shapes. The disk slot operand indexes 16-bit handles, and each child starts at its first detail program with condition byte `0xf9`. It inherits the current transform and scale. Vertex storage remains shared: weapon programs deliberately use high vertex slots, and those writes survive the return. The parent translation and condition are restored. All nested models share the instruction and depth budgets. Emitted primitives retain their attachment slot for loadout selection.

```sh
python3 tools/check_attachments.py --build build --research ../tfx-reverse
```

Twenty original-handler executions verify present/absent handles, anchor installation, child condition and parent restoration. A separate comparison covers **1,452 complete preview loadouts**: all 22 selectable stores, each of ten mounts and all mounts together, on each of the three player aircraft and their three dedicated arming models. Every primitive and vertex agrees with the independent inspection interpreter. This latter comparison does not establish complete native camera projection or raster equivalence. Asset-free tests also exercise shared vertex storage, absolute child scale, absent stores and recursive malformed programs.

### Original arming controls, readouts and preview camera

```sh
python3 tools/check_airframes.py
python3 tools/check_arming_controls.py
python3 tools/check_arming_screen.py
python3 tools/check_orbit_camera.py
```

The external executable supplies arming labels, hit rectangles, aircraft preview names, slot pairs and label positions. Aircraft store mounts and fuel capacity are decoded from literal assignments in the original compiled initializers. The Eurofighter and F-117 base moments retain their original square-root and ordered multiplication calculations; all **99 double fields agree bit for bit** with the three native initializers.

The controller owns its temporary mount markers separately from actual inventory. Markers participate in the original F-117/F-22 exclusion rules while compatible slots are marked sequentially. Placing and clearing affect the paired slot too. Escape selects the mission's defaults only if the native model table is empty, including its temporary markers; placeholders are then removed on exit. Right mouse cancels placement. The original strict rectangle edges, pointer adjustment and last-match precedence are retained. **3,072 native placement/clearing/exit sequences and 7,241 native hit tests agree.** Input-release waits and 3D picking are explicitly outside these controlled calls.

**192 complete arming widget frames agree pixel for pixel**, covering all aircraft, all selectable stores, scrolling positions, empty and mixed loads, mass, drag and inertia. The original drag display uses the preceding frame's accumulator. Watcom silently drops a malformed trailing percent sign in its format string; this omission is preserved. The comparison supplies original background artwork at the image-driver boundary and excludes 3D preview drawing; original formatting, font painting, outlines and arithmetic execute.

The arming screen uses `efa_glob`, `f17_glob` and `f22_glob`, which have dedicated mount-selection collision boxes. Original startup issues event 5 after the fade-in; the latter two definitions use it to open their weapon bays. The preview camera uses native `0xdabd8`, whose shift/negation order differs from the ordinary component matrix. Native `0xb9b7a` also orbits with a one-table-step phase offset at zero. **4,121 complete view matrices and signed Q16 camera positions agree exactly.** Custom projection origins leave the existing flight projection's operation order unchanged.

The aircraft, control, widget and camera comparisons, plus all 43 CTests, pass in development, Release and ASan/UBSan. These are subsystem comparisons; the assembled 3D screen and its live flight handoff remain in progress.

### Live arming screen and flight handoff

Normal campaign flight now opens arming unless the mission explicitly requests default weapons. It uses the original dedicated aircraft, carried-store and empty-pylon models, including the small aircraft pointer and rotating weapon previews. Store selection creates compatible mounting markers; the aircraft's original SSD collision entry picks a mount and fills its paired mount. Right mouse ends placement. The chosen inventory passes into flight without being replaced by the default fit. Direct mission launches retain automatic default fitting for analytical runs.

```sh
python3 tools/check_arming_picks.py
./build/arming_preview_probe /path/to/TFX flow
python3 tools/check_frontend_window.py --data-dir /path/to/TFX
```

**12,860 original mount selections agree**, covering each aircraft's actual selection boxes, directed edge cases, swept pointer segments and the initial zero position. The original query transform and SSD event dispatcher execute. The native actor draw wrapper also agrees with **60 complete arming bay-animation states**: arming holds the animation-enable byte at one, so these streams advance per draw rather than using the flight world's seven-tick animation clock. The original opening event is captured directly from the complete arming startup before its input loop.

The view setter stores **rows**, used directly as right/down/forward. The model vertex multiplier produces Q15 values while actor and camera translations use Q16, so arming geometry uses half-sized model units. Native model projection shifts signed Q16 X/Y by eight and divides by signed integer depth, truncating towards zero. **4,096 complete vertex products and 4,096 projected vertices agree**, alongside the earlier 4,121 camera states. The existing flight/inspection camera retains its continuous projection and operation order.

The unavailable-store panel and mounted-store labels agree in **82 complete original frames**, in addition to the 192 normal widget frames. Their rectangles include both far edges. These native solid spans require the actual A0000 VGA aperture; the harness now optionally relocates the data object using the executable's LE records, leaving the original raster instructions unchanged. Existing planner/font captures retain their previous default memory arrangement. The assembled arming screen also agrees with **81 complete palette frames** covering the original forty-stage fade-in, forty-stage fade-out and final black.

Headless pointer flows select, place and retain the intended paired stores on all three aircraft. A private X11 test also selects AIM 9S, mounts it, ends placement and launches FWS flight with the original DONE button; it repeats after pilot reload and still covers Tour review/arming/flight. No user installation, saves or desktop input are modified.

These comparisons establish the controlled subsystem boundaries above. They do not yet establish a complete original 3D arming-frame match. Full modal quit handling and input-release timing remain separate work, as do the broader flight-renderer and loadout/aerodynamics integrations.

The assembled-screen comparisons, three pointer flows and all 43 CTests pass in development, Release and ASan/UBSan. The private custom-arming window flow passes in development and Release. The shared capture changes also preserve all ninety complete planner map pages and 576 HUD-font frames, and all 128 retail mission starts still render successfully.

### HUD sprite and embedded-mask painters

```sh
python3 tools/check_hud_images.py
```

Shared sprite painting now serves the menu pointers and cockpit instruments. The original four-pixel right-edge clipping, transparent sprite index zero, MSB-first monochrome rows and explicitly painted black pixels are retained. Embedded masks use rounded-up byte strides, including widths that are not multiples of eight.

**572 complete native pixel-and-coverage frames agree** across all frames in eighteen recovered HUD banks and thirty-two embedded mask addresses, including edge clipping and black ink. The 144 menu-pointer frames still agree after sharing the painter. These comparisons and all 43 CTests pass in development, Release and ASan/UBSan. This verifies the instrument drawing primitives; live HUD composition is the next integration step.

### Cockpit clock, fuel, throttle and countermeasures

```sh
python3 tools/check_readouts.py
```

Typed telemetry now feeds the original clock, fuel, throttle, ECM/stealth and chaff/flare readouts. Their labels, formats, warning thresholds and coloured-font mapping come from the external executable. The clock uses a wrapping 32-bit tick sum and 54 ticks per second. Throttle percentages truncate the extended product towards zero; low fuel switches from coloured sprite digits to the small HUD font. ECM takes precedence over stealth, and the F-117 omits the separate stealth label.

**504 complete native pixel/coverage/status frames agree**, including each warning threshold, fractional values, countermeasure counts, clock overflow, horizontal plane phases and the distinct bottom-edge clipping rules. Original Watcom formatting executes in the comparison, including floating fuel values. The existing 576 HUD-font frames still agree after adding optional coverage recording. These comparisons and all 43 CTests pass in development, Release and ASan/UBSan. The readouts are ready for the assembled cockpit; flight still uses its diagnostic overlay while that composition is implemented.

### Multifunction-display instruments

```sh
python3 tools/check_mfd.py
```

Seven original page painters now consume typed flight, fuel, damage and inventory telemetry: stores, gauges, flight data, four fuel cells, system warnings, aircraft schematic and engine load. Their backgrounds, monochrome masks, labels, positions, display mount ordering, formats and conversion factors come from the external assets. Selected stores retain the original readiness colours and aircraft-specific mount arrangement; failed systems retain their outlined cells. The fuel display preserves the signed-word comparisons inside its dword subtraction loop.

**588 complete native pixel/coverage frames agree**, covering both outer display positions, all three aircraft, damage states, fractional values, viewport clipping and fuel-cell boundaries. All **eighteen original outer-page selections** agree independently. The two dispatch tables differ: the right display adds the moving map and engine load, while the left supplies the aircraft schematic and ground database; gauges occupy different indices. Scene-dependent camera, ground database, moving-map and control/autopilot pages remain separate integration work.

The HUD width helper also agrees for all **576 font cases**. Native `0x87114` measures the full character byte instead of the painter's masked index, and its partial-register operation retains the upper word for negative mapping entries. Centred MFD labels retain the original signed low-word conversion. The comparison executes those original instructions rather than deriving expected widths from the C++ mapping.

The MFD, readout and font comparisons and all 43 CTests pass in development, Release and ASan/UBSan. These remain verified pieces of the forthcoming cockpit composition, rather than a claim of a complete flight frame.

### Compiled cockpit artwork

```sh
python3 tools/check_overlays.py
```

The bitmap compiler's restricted literal pixel/plane streams now decode into indexed artwork records. Canopy column-entry tables become bounded data with their original horizontal-byte and vertical-row offsets. The fixed missile/map overlays retain their fixed placement, even when offset arguments are supplied. Explicit black writes retain coverage separately from untouched pixels. No original x86 code executes in the game.

**68 complete native pixel/coverage frames agree** across `infcock.hud`, `cockpit.bin`, its `a.bin` alias, `misshud.hud` and `cockmap.bin`, including extreme legal horizontal pans and vertical shifts. Asset-free tests cover every truncated prefix, unsupported tokens, invalid plane masks, out-of-screen addresses, unused bytes and fixed-overlay argument handling. The native captures and all 44 CTests pass in development, Release and ASan/UBSan. Viewport selection, the companion lower-panel upload and flight composition remain separate integration work; decoding retained artwork does not establish that every resource is selected in retail flight.

### Warning and auxiliary indicators

```sh
python3 tools/check_warnings.py
python3 tools/check_auxiliary.py
```

The warning-lamp painter retains the original gear, wheel-brake, hook, autopilot, warning/caution, fire, lock/launch, stall and threat sprite selection. It consumes typed system conditions and explicit display flags. Its four-draw phase and threat-sound latch belong to the painter's persistent state. Clearing the threat does not reset that original one-shot sound latch. Original lamp artwork and code consumers establish these meanings; nearby flags are not assumed to describe afterburner or ground contact.

**1,024 complete native pixel/coverage/phase/sound frames agree**, including every system's failure/intermittent warning and tracked-weapon category branches. Another **512 complete native pixel/coverage/refresh-state frames agree** for engine lamps, approach cues, ground indicators and afterburner markers. The engine-cache bytes are read but not rewritten by this native region. Afterburner pips are paired 2×2 points, rather than line segments; their original linear VGA edge wrapping is preserved. The approach-cue ordinal remains explicit until its selecting flight logic is ported.

These comparisons, the existing MFD/readout comparisons, and all 44 CTests pass in development, Release and ASan/UBSan. Sound requests are compared as events; the mixer and complete HUD composition remain in progress.

### Per-viewport HUD clipping

```sh
python3 tools/check_clipping.py
```

The renderer now owns explicit glyph and sprite clipping state. Native `0xc0634` keeps the supplied glyph X limit, rounds sprite X limits to four-pixel VGA groups, and increments bottom Y for both. Instrument painters consume that state; their earlier controlled inspection-driver limits remain the default until a viewport is selected. The sprite painter also retains the original planar edge reads when both horizontal sides are clipped with unrounded initial limits, reconstructing them within owned image storage.

**1,601 complete native pixel/coverage frames agree**, covering eighteen original sprite banks, embedded masks, every character byte, interior display rectangles and directed/synthetic plane-boundary cases. The 572 image, 576 font/width, 588 MFD, 504 readout, 1,024 warning, 512 auxiliary and 144 menu-pointer comparisons still agree. These checks and all 44 CTests pass in development, Release and ASan/UBSan. This supplies the clipping transitions needed by the moving map and assembled HUD; it does not yet replace the diagnostic flight overlay.

### Scrolling cockpit map

```sh
python3 tools/check_moving_map.py
python3 tools/check_attitude.py --data-dir /path/to/TFX
```

The moving-map painter owns its schematic and blink state, borrowing typed Q8 aircraft/surface contacts and integer-world targets for each draw. It preserves separate coordinate division before subtraction, north-up scrolling, the heading arrow, strict marker borders, aircraft altitude filtering, stealth suppression, target/navigation colours and native clipping restoration. Elapsed ticks are added per map draw; even a large elapsed interval toggles the marker colours at most once in that call. A shared painter must therefore serve both map locations when both are visible.

**320 complete native pixel/coverage/blink/clip frames agree** across all five original regional schematics and the centre/right display rectangles. The native actor-enumeration boundaries receive supplied lists; map projection, filtering, sprite drawing and marker painting execute unchanged. The shared signed-word planar rotation also agrees in **5,120 native cases**, covering every lookup-table phase and extreme inputs; the existing direction, basis rotation, normalisation and angle checks remain unchanged and still agree.

These comparisons and all 44 CTests pass in development, Release and ASan/UBSan. Binding the environment schematic and live flight contacts into the assembled HUD remains part of cockpit integration.

### Horizontal and beyond-visual-range radar

```sh
python3 tools/check_radar.py
```

Both central radar views now use their original display sprites, range/divisor tables, signed-word rotation and authored BVR envelope. Supplied aircraft/surface/projectile records preserve native Q8 positions. The horizontal view retains role and stealth filtering, selected-aircraft blocks, blinking radiating defence sites (`defop1`–`defop3`, type 56), projectile ownership colours and excluded cannon/decoy records. The BVR painter has its own filtering rules and does not apply the horizontal painter's failed-radar early return. This is a statement about these drawing routines, not a complete damaged-flight session.

Intermittent-radar samples consume the shared gameplay generator in original draw order. Allied surface markers bypass that sample in the horizontal view, while BVR samples them. Projectile cross arms remain visible independently of the sampled blinking centre. The horizontal pulse changes even when a subsequent stealth/failure gate suppresses contacts; BVR does not advance that pulse.

**640 complete native pixel/coverage/pulse/random-state frames agree**, covering both modes, every range, all aircraft, system conditions, selected contacts, surface types, projectiles and viewport offsets. Native actor-enumeration and fixed definition-type lookups receive declared input records; original projection, filtering, formatting and VGA drawing execute. Shared one-pixel and 2×2 marker painting also preserves all 512 auxiliary frames. The radar, auxiliary, map and MFD comparisons and all 44 CTests pass in development, Release and ASan/UBSan.


### Controls and autopilot instruments

```sh
python3 tools/check_controls_display.py
```

The controls MFD now draws the original surface pointers, F-22-specific indicators, flight-configuration labels and all five autopilot modes. Its artwork, formats, display scales and conversion constants come from the executable. The separate autopilot indicator preserves the original mode number even when the autopilot is disengaged. This establishes the displays; the autopilot controller itself remains separate work.

**768 complete native pixel/coverage frames agree** across both MFD positions, all three aircraft, modes, configurations, deflections and instrument offsets. Another **256 frames agree** for the autopilot indicator, including signed mode-number boundaries. Native Watcom formatting and the original VGA line painter execute in the comparison. Pointer endpoints stay within the native scanline table, whose out-of-range reads are undefined. The earlier 588 MFD and 504 readout comparisons continue to agree.


Scene submissions now seed the model condition byte from SSD part parameter zero, following native `0xcc001` and `0xbac16`. Previously the scene adapter copied the parameter array but left this separate initial condition at zero, preventing state-selected geometry such as the water-crash effect from selecting its authored branch. The original queue-to-dispatch path independently agrees for all 256 byte values; this corrects scene context, not model decoding or full-frame renderer fidelity.


### Assembled instrument HUD

```sh
python3 tools/check_hud.py
```

The instrument compositor follows the complete original `0x803e8` draw order: range notice, readouts, left/centre/right MFDs, warning lamps, autopilot selection, then auxiliary indicators. Fuel status changes before the MFDs and warning lamps consume it, and is returned for the caller's system state. Both outer display dispatchers retain their previous page and request the original shared redraw on a change. Both moving maps share one blink clock; radar faults consume the same generator as gameplay. Aircraft and surface contacts, projectiles, targets and navigation are explicit borrowed inputs.

**504 complete native pixel/coverage/animation/clip/random-state frames agree**, exercising all three aircraft, every currently implemented outer page, all centre modes, warning thresholds, page transitions and contacts. The original instrument routine runs as a whole; archive access, actor enumeration, surface-type lookup and warning sound output are declared boundaries. The separate upper aiming HUD is explicitly disabled in this capture, and the scene-camera pages remain a separate rendering consumer. Flight integration is the next step.

The manual also identifies the control MFD's trailing/leading-edge flap pointers and F-22 thrust-vector indicators. Flight-state comparisons establish that the four lower-left pips show afterburner stages (`0x1496d`), so the earlier provisional ammunition name has been corrected without changing their painter.


### MFD scene-camera requests

```sh
python3 tools/check_scene_displays.py
```

The FLIR/DLIR and ground-target database now prepare the original integer camera positions and view angles. The F-117 retains its ±45-degree free-camera gimbal limits. Target bearings, two-draw reticle phase, the fixed-distance ground orbit, height clamps, heading increments, range labels and reticle masks follow their original handlers. The scene consumer uses the independently verified native view matrix and projection origin.

**2,304 native cases agree** in camera requests, persistent gimbal/orbit/reticle state and all overlay pixels, across both displays, all aircraft and three orbit-step seeds. Full world rendering and the projected reticle point are declared boundaries; this is not a complete 3D pixel comparison. The assembled 504-frame instrument HUD and 1,601 clipping comparisons continue to agree, as do all 44 CTests.

An original bug is explicit: `0x88378` reads a roll word after `0xc9714` writes only pitch and heading. It can therefore inherit previous stack contents (the capture exposed a prior ground-camera height). The comparison supplies this otherwise unwritten input deliberately. The new native host will supply zero rather than depend on uninitialised C++ memory; a future DOS trace can establish whether a stable retail value deserves reproduction. Reticle testing also corrected monochrome painters to sign-extend their word coordinates, including MOVZX arguments that wrap at the top or left edge.


The original MFD key callbacks are now represented by the selection state: 1/2/3 cycle their respective displays, R decreases/wraps the active radar range, the F-117 skips BVR, the left ground database is skipped without authored targets, and the right camera page has its original aircraft/weapon-category eligibility. Wrapping to the first page happens at draw time. **1,920 native cases agree**, including word boundaries and the signed normalization rules (`tools/check_display_controls.py`). Environment configurations now supply their authored schematic basename rather than inferring one from the terrain filename; palette, night flag and map bindings agree for **all 33 decoded native environments** (`tools/check_environment_bindings.py`).


### Live instrument integration

The flight host now binds the instrument compositor to live player pose, engines, throttle, fuel, faults and stores; it supplies aircraft, mobile-surface and projectile contacts in native enumeration order. Both MFD scene pages use the recovered camera requests with the existing software world renderer. Original 1/2/3/R/N display controls are connected, fuel-status feedback returns to the system state, and pausing retains the completed frame rather than advancing instrument animations. The host requests indicator refreshes because it repaints the whole framebuffer.

The outer player callback's fuel-gauge/burn filter is also translated: **4,246 native cases agree**, including signed-word boundaries and the minimum burn estimate. This feeds the flight-data page's range estimate instead of inventing a fuel-flow approximation (`tools/check_fuel_gauge.py`).

A private X11 test exercises store and cannon firing, all three MFD key paths (including scene-camera pages), range/target keys, pause stability, designator controls and mission termination. **All 128 retail missions start with the live HUD**, and another pass advances **1,024 simulation steps in every mission under ASan/UBSan** before drawing. The existing 44 CTests and Release/HUD comparisons pass. These are integration checks, not complete native flight-frame comparisons. Static cockpit framing, upper aiming symbology, radio layout, full view selection and remaining flight-system bindings are still being connected; their diagnostic adapter remains visible.


### Default cockpit and instrument startup

```sh
python3 tools/check_cockpit_setup.py
python3 tools/check_cockpit_frames.py
```

The native viewport table begins at DATA `0x5da4` / file `0xf3848`. Its projection row, panel/overlay bindings, bottom edge and callback form a 20-byte record with the callback at offset 16, called by `0x73f4b`. The earlier research decoder began four bytes too early and associated each view with the preceding callback; it has been corrected in `tfx-reverse`. The preceding DATA `0x5da0` byte is a separate effect flag. **All 29 corrected native records agree.** The forward cockpit is view zero, with its original `infcock.hud` overlay, 55-row planar panel and instrument callback.

Native `0x7df30` overwrites the stored instrument defaults at mission startup. It selects flight data on the left, 50/100-mile radar ranges, full fuel gauge, fifteen chaff/flares and the lowered cockpit. The F-117 begins in stealth with a central map and right-hand systems page. Engine/gear indicators distinguish airborne and landed starts. **All six aircraft/start combinations agree.** Animated Page Up/Page Down follows the original 22-position sequence; **2,048 multi-frame steps agree**, including a full-height view interrupting motion.

The live host now paints that cockpit artwork and uses the native viewport projection origin. The existing approximate horizon respects the selected origin/focal length; the complete original sky/weather renderer remains separate. **198 complete pixel/coverage/offset/origin frames agree** against original composition across six views, three horizontal offsets and vertical clipping boundaries. The compiled overlays execute unchanged in the comparison. The VGA-to-VGA panel transfer is a declared hardware boundary: its original source/destination rectangle is applied to independently deplaned source bytes. Projection setup is checked with the clamped coordinates; this is not a complete pre-render camera-order comparison. The missile view's five-byte `.hdd` placeholder has no visible footer and is intentionally not decoded as a bitmap.


The setup, positioning and frame comparisons pass in development, Release and ASan/UBSan. Real-window MFD/designator/weapon/result checks still pass with the restored cockpit, as do all 44 CTests. Every retail mission starts successfully, including a further sanitizer run after 1,024 simulation steps per mission. The upper aiming and radio adapters remain the next visual integration work.


### Upper-HUD flight readouts

```sh
python3 tools/check_hud_text.py
```

The original numeric upper-HUD painter (`0x7f8e0`) and independent air-brake, brake-chute and arrester-cable labels (`0x7eb7c`) now have a dedicated renderer. Altitude, airspeed, Mach, load, map coordinates and throttle retain their original strings, word-coordinate wrapping, alignment and float/double storage boundaries. Watcom rounds a stored double after decimal scaling and suppresses the sign of rounded zero; host `printf` alone differs at values such as `0.005` and `1.015`. The reconstruction preserves this distinction for these unpadded readouts.

**768 complete native pixel/coverage frames agree**, including adjacent doubles at decimal-rounding boundaries, all independent message combinations, negative/positive telemetry and ten instrument/clipping offsets. Original formatting and VGA text execute in the comparison. This verifies the painters from supplied telemetry; their live upper-HUD dispatcher and remaining aiming symbology are still being connected.


### Heading strip and pitch ladder

```sh
python3 tools/check_attitude_display.py
```

The original forward-HUD heading strip (`0x80ffc`) and pitch ladder (`0x80ab8`) now render from their original sprite banks and 42 authored mark records. The ladder retains the 36-point, 1,820-angle-unit circle with three wraparound entries at each end, separate pitch/roll projection matrix, five visible marks, roll rotation, solid/dashed segments and VGA-group sprite clipping. Its projection remains distinct from the model renderer's camera matrix.

**1,024 complete native pixel/coverage frames agree**, including steep/inverted attitudes, table-step boundaries, independently varied projection angles and ten instrument offsets. The native angle setup, projection, clipping and all raster loops execute; only resource resolution supplies original bytes. This comparison also corrected the shared line clipper: native `0xbf53d` measures from the farther endpoint before truncating, which can move a clipped ladder edge by one pixel. Patterned lines preserve the original plane-mask phase and X-major final-endpoint behavior. Live dispatcher integration follows separately.


### Non-firing cannon prediction

```sh
python3 tools/check_cannon_prediction.py
```

The HUD trajectory helper `0xa2878` uses a private temporary cannon shot: five warm-up updates, then up to eight updates before each of five displayed samples, at twenty native ticks per update. Ground contact or an ended motion callback stops further advancement. The trajectory neither enters the live projectile pool nor consumes ammunition. The caller's movement-height bounds are explicit inputs; the earlier projectile comparisons supplied different bounds from the executable's stored defaults, so those controlled defaults are no longer assumed by this predictor.

**512 native trajectories and 2,560 Q8 samples agree**, including ground/ceiling boundaries, varied limits, inverted attitudes and negative/positive speeds. Original construction and motion callbacks execute with a supplied transformed launch anchor; screen projection is observed at its boundary. The native helper also restores its caller's elapsed timer. Mount transforms and projectile motion retain their separate comparisons; live aiming composition is the next consumer.


### Forward weapon HUD and live aiming integration

```sh
python3 tools/check_weapon_display.py
python3 tools/check_weapon_display.py --full
python3 tools/check_cannon_prediction.py
python3 tools/check_impact_prediction.py
python3 tools/check_window_controls.py --data-dir /path/to/TFX
```

Original navigation, air-to-air and air-to-ground layouts now use the authored sight masks, labels, ammunition text, range-dependent reticles, suppression cross, ARM/LOCK labels and pitch ladder. **768 complete native layout frames agree**, including all aircraft, cannon/stores, lock flags, independent projection angles and eight offsets. Another **768 forward-composition frames agree**, executing original `0x800f4` with supplied cannon/impact screen samples and declared exclusions for the acquisition and cannon-selection controllers. These cases omit selected target contacts, landing approach and temporary BINGO/PULL UP warnings; they establish composition in the supplied context, not a complete cockpit/frame claim. The heading strip and cannon trace change the line viewport inherited by the later pitch ladder; this context is now explicit.

The original Mk82 impact predictor (`0xa29dc`) also runs independently of live projectiles. It keeps the bomb at its mount during the initial attached stage, advances at ten ticks per update and stops at ground/lifetime termination. **256 complete native trajectories agree**, including varied height limits, inverted flight and boundary starts, with the caller timer restored. The native category-9 set contains the Mk82; other bomb guidance categories use their own consumers. The impact marker is drawn inside its authored bounds, while its connecting line is always clipped to the weapon viewport.

All **36 sight-mount lookups** agree with native `0x8b984`, including pylon -1 and the cannon sentinel. Those sentinels read adjoining stored records rather than a separately authored cannon anchor for every aircraft; their bytes are retained. Ordinary carried-store and firing-cannon mounts remain separate.

Live flight now paints the verified readouts/heading/weapon layout before cockpit artwork and lower instruments, replacing the temporary top-of-screen diagnostic labels. F returns to navigation; weapon selection also retains the cannon's selected air/ground role. HUD faults retain the original intermittent/failed gate. Sensor acquisition now uses the actual forward-cockpit projection origin. Projected trajectories currently use the existing approximate world camera and stored movement bounds; original world initialisation/projection and complete-frame/session verification remain open. Target outlines and radio placement still use their integration adapter. The private-window checks exercise firing, display cycling, scene MFDs, pause, designator controls and result handoff, and all 128 retail missions start successfully with the new forward HUD.

The forward composition, cannon/impact trajectories and sight-mount checks pass in development, Release and ASan/UBSan. All 44 existing CTests pass, and all 128 retail missions also draw after 1,024 simulation steps under sanitizers. These remain subsystem and integration checks rather than a complete original-session comparison.


### Scrolling radio messages

```sh
python3 tools/check_radio.py
python3 tools/check_radio.py --frames
```

The original radio controller (`0x81174`–`0x813c3`) now owns its message history, cursor, timing remainder and optional repeating pass. Messages retain both 20-character padding runs and native uppercase/digit filtering; the 19-character window is copied before advancement, and the final partial window is suppressed. Ordinary scrolling uses four ticks per character and time warp uses twenty. Clear, replacement and replay deliberately retain the timing remainder.

**4,096 native state/window updates agree**, including empty, mixed-case, punctuation, extended-byte and NUL-terminated messages, replacement, clear, replay, repeated messages and both timing modes. Another **512 complete native pixel/coverage/state frames agree**, including both original fonts, view-zero offsets and clipping. Original string preparation, controller and VGA font painters execute with the external pitfont bank supplied unchanged.

Live mission, aircraft and surface-unit radio events now feed this controller, replacing the temporary five-second full-line label. The coloured radio display renders after the auxiliary instruments at the original cockpit position. Plain L invokes the original replay branch; Alt+L's separate landing controller remains unimplemented. Paused frames retain the current window. Other camera modes still await their complete native callbacks.

The radio state/frame comparisons pass in development, Release and ASan/UBSan. The 504-frame original instrument-HUD comparison still agrees, all 44 existing CTests pass, and private-window firing, MFD, replay, pause and mission-result checks pass with live radio rendering.


### Target telemetry and marker painters

```sh
python3 tools/check_target_display.py
```

The original target-information painter (`0x7f59c`) retains the uppercased first word of the aircraft name, signed-word speed conversion, heading scaled by 360/65,536, unsigned altitude and horizontal range steps. The direction cue (`0x7f000`) preserves wrapped matrix products and native angle-helper behavior, including phase zero when either reduced input is within -1..1. Both sizes of primary/acquired masks are decoded directly from the executable. The edge-marker helper (`0x7ee9c`) clips toward the secondary marker's top-left corner before painting it; its caller uses this while the seeker is acquiring, rather than as a general minimum-range indicator.

**1,600 complete native pixel/coverage frames agree**, covering all five painter paths, names, signed telemetry, matrix overflow, projected/tracking points, eight cockpit offsets and four clip rectangles. The external aircraft-name lookup supplies text; native name conversion, formatting, geometry and VGA painters execute. Decimal readout formatting is shared with the already verified upper-HUD painter, and line clipping is exposed without changing its verified arithmetic. Live target-state composition follows separately.


### Live target composition and lock animation

```sh
python3 tools/check_target_tracking.py
```

The forward HUD now combines the original selected-aircraft data, heading chevron, target/direction markers and seeker-acquisition/lock overlays. The chevron rotates its three authored points by target heading minus player heading. The controller owns the retained normal/compact sight selection, nine-frame lock blink and previous-lock latch. Navigation draws retain this state rather than updating the latch. Failed/intermittent HUD gating remains in the calling flight host.

**1,024 original forward-HUD frames agree in pixels, coverage, retained animation and lock-cue requests** across selected/missing contacts, acquisition, confirmed/lost locks, suppressed radar cues, weapon changes, navigation, ground designation, offsets and resets. Original layout/controller/text/raster code executes. Sensor/selection state, world-screen projection and cannon/impact samples are supplied at their separately checked boundaries; audio/voice requests are observed without playback. These are supplied-state sequences, not complete simulated engagements.

The ground outline retains the original fixed X clipping limits and category-11 anti-radiation exclusion. Live flight binds actor profile names, Q8 position, heading, Q16 speed, player orientation and verified seeker state to these painters, replacing the temporary white tracking box and ground-target footer. Native navigation-contact cues, landing-approach guidance, temporary BINGO/PULL UP warnings and other view callbacks still need their own consumers. Lock-cue effects are returned for the pending audio backend.

The target-controller comparison passes in development, Release and ASan/UBSan, as do the 1,600 standalone target-painter frames. The existing 768 forward-composition frames still agree under sanitizers. All 44 CTests pass; private-window checks cover firing, display controls, paused target state and result handoff, and all 128 retail missions run 1,024 simulation steps under sanitizers.


### View selectors and transition queue

```sh
python3 tools/check_view_controls.py
```

The original ten function-key selectors now share an owned ten-entry view queue, retained cockpit offsets, low-memory alternatives, orbit matrices and fixed fly-past position. Intermediate viewport indices are named separately from final camera modes. Consumption occurs only after the current camera stage signals completion; a full queue drops further requests, and leaving a missile view discards the old queue. Shift+F1 and missile infrared retain the native save/restore rules. F5 deliberately has a different automatic-landing gate from the other keys. F9 compares target pointers before checking null, so two missing pointers still queue the ground-distance target view.

**9,690 native selector/queue updates agree** across all 29 initial views, all ten keys, blocked controls, low-memory mode, repeated requests, full queues, offsets and varied player poses. Original matrix rotations and fixed-camera placement execute; target selection is supplied at its external boundary and optional fly-past sound requests are excluded. Development, Release and ASan/UBSan comparisons pass. This establishes selection state; live camera motion and drawing are the next integration step.


### Head, chase and target camera integration

```sh
python3 tools/check_view_cameras.py
python3 tools/check_view_controls.py
python3 tools/check_window_views.py --data-dir /path/to/TFX
```

The camera dispatcher now retains the original head lift, yaw/pitch limits, head-turn stages, return-to-panel movement, chase smoothing/ground limit, fixed fly-past placement and automatic chase handoff. Tactical and target-observer cameras consume explicit selected contacts. Virtual-cockpit target tracking retains its original directional limits, roll gates, lost-contact recovery queue and automatic resumption. The view-matrix generator and Q16 orbit-position helper are shared with the separately verified arming camera. Full-world scene positions are unwrapped around the native terrain anchor without changing the original wrapped Q16 translation.

**11,776 native dispatcher updates agree** across twenty-three view modes (including the missile extension below) in retained state, complete camera matrices, Q16 positions, automatic queue changes and internal/side/exterior player-model requests. Cases include rotated world/orbit matrices, signed-angle wrapping, pan input, ground limits, missing contacts and target loss. Original camera/controller/matrix code executes; supplied player/target poses and ground heights are explicit inputs, while navigation contact selection, world-driver configuration, weather advancement and actual player-model rendering are declared boundaries. The native target observer's variable-shift height-anchor quirk is retained independently of its camera translation.

The comparison passes in development, Release and ASan/UBSan, as do all 9,690 view-selector updates. All 29 viewport records and the existing 198 cockpit-composition frames still agree. The existing 12,860 arming mount picks and 60 native arming-animation draws also pass after the shared-math change. Private-window checks cover chase/full/head/rear/tactical/target/virtual keys, cockpit-offset restoration, paused-frame retention, existing firing/MFD/designator controls and result handoff.

Live flight selects the appropriate forward-HUD callback, preserves radio placement in other views and restores cockpit offsets after transitions. F1–F10 are connected, including the missile extension below; recovery/ejection cameras, the separately restored external-view information painter and complete frame/session verification are described below. Inspection also exposed the model-scale clipping limitation corrected below.

All 44 CTests pass after rebuilding every development target. These camera-state checks remain distinct from complete world-frame equivalence.


### Model-scale clipping and virtual canopy

```sh
python3 tools/check_orbit_camera.py
python3 tools/check_scaled_clipping.py
python3 tools/check_window_views.py --data-dir /path/to/TFX --mission 601
```

The virtual-canopy models use an authored camera scale of 400. The earlier scene painter converted their vertices into world units but discarded that scale before near clipping, removing the entire canopy. Vertices now retain world units per native camera unit through polygons, lines, particles, carried-model attachments, facing tests, clipping and projection. The factor between Q15 model products and the Q16 camera loop is explicit. The original opaque canopy and static MFD textures consequently render in the live virtual and head-turn views.

Original integer projection restores the native Q16 coordinate grid after unit conversion. This avoids a floating-point rescaling artefact where an exact depth such as 29 became 28.999999999999996 and selected the wrong integer divisor. No palette interpolation or artwork resampling is introduced.

The existing **4,121 native matrix/orbit cases, 4,096 native model projections and 4,096 native model-vertex products agree**, with **36,864 additional rescaled projection cases** including exact depth boundaries, fractional signed coordinates and canopy units. A separate property check compares complete software output for **1,287 polygon/line/point cases** across nine unit scales, including near-plane crossings; this establishes clipper scale invariance, rather than claiming original complete-raster equivalence. Carried-model tests also check inherited and replaced projection units.

These checks pass in development, Release and ASan/UBSan. All 44 CTests pass. Private-window camera/offset/pause checks pass in missions 501, 601 and 701; scratch captures permit visual inspection of the authored canopies. All 128 retail missions run 1,024 simulation steps and draw under sanitizers with the corrected path. Complete world transform/order, clipping/raster boundaries, camera callbacks and session equivalence remain separate work.


### Native world-point projection

```sh
python3 tools/check_point_projection.py
```

The original HUD/world-point projectors (`0xc5759` and `0xc57d1`) now have explicit integer-coordinate and Q16-coordinate consumers. They retain word-relative subtraction, separate signed high products for fixed coordinates, wrapped matrix rows, the inclusive 16–20,000 camera-depth range, truncated reciprocal and signed high-product screen conversion. These paths differ from the polygon vertex projector. Invalid points retain the original `(-1,-1)` result at live call sites.

**16,384 native cases agree**, covering both routines, arbitrary stored matrices, coordinate/angle-origin wrapping, fractional camera positions, near/far boundaries and negative screen rounding. Original matrix/translation setters and both complete point routines execute without intercepted dependencies. Another 182 compact synthetic native cases run in the asset-free CTest suite.

Live acquisition uses the verified projector with the existing forward-camera adapter. Cannon/Mk82 prediction and designated-ground outlines use the active camera's stored matrix, Q16 position and projection origin. Predicted Q8 coordinates are shifted to integer world coordinates before the word projector, as in the original callers. Complete sensor/camera lifetime ordering, navigation/approach consumers and full-frame/session equivalence remain separate integration work.

The native comparison passes in development, Release and ASan/UBSan. All 45 CTests pass; private-window checks still cover air/ground firing, acquisition-related controls, radar/MFD pages, designation, pause and result handoff.


### Fired-store and impact cameras

The F8 camera follows the latest player-fired store, excluding cannon and countermeasures, as selected by native `0xa2f1b`. A second press enters its forward/nose view and uses the original missile overlay. The follow camera retains the last projectile pose, original Q15 orientation composition, one-fifth position smoothing, pan increments and distance growth after the projectile ends. Its queued handoffs lead to tactical, impact-orbit or fixed fly-past views. The current live impact observer follows the first fatally damaged aircraft until its retirement; surface/scenery/player-crash observer lifetimes still need their selecting consumers.

The expanded native dispatcher comparison covers **23 modes and 11,776 persistent updates**, including live/missing missiles, valid nose views, impact contacts, queued fallback, all previously covered camera modes and their model selections. All **9,690 selector updates** still agree. These comparisons pass in development, Release and ASan/UBSan. All 46 CTests pass, and private-window checks now fire a store, enter both F8 views, return with F1 and continue the existing cannon/MFD/designator/result checks.

One original unsafe case is handled explicitly: the nose-camera dispatcher queues its follow-view fallback when the missile is missing, then continues to read through the null missile pointer. The C++ host retains the last valid camera pose during that handoff. This boundary is covered by an asset-free lifecycle regression rather than claimed as a defined native-memory comparison. The original infrared palette, other lighting changes and remaining camera artwork remain separate renderer work.

The preceding native world-point integration also passes the full 128-mission, 1,024-step ASan/UBSan run after its live caller changes.


### External-view flight information

```sh
python3 tools/check_external_display.py
```

The external-camera callback now draws its original altitude/speed/heading strip. The panel retains underlying palette bits through AND-15 / OR-128 operations, then paints the original borders and seven-row fixed-font labels with one-pixel shadows. Altitude and speed products retain their original stored-double formatting boundary. This uses the presentation fixed font, independently of the smaller forward-HUD font. Live chase, tactical, fly-past, target and impact views receive the current player telemetry.

**512 complete original pixel/coverage frames agree**, including enabled/disabled strips, positive/negative telemetry, heading wrap and all 256 background indices. The original polygon scanner, VGA logical operations, formatter and fixed-font painters execute; the already checked radio consumer is disabled at its own boundary. The comparison covers the full 320×200 external viewport, rather than claiming arbitrary clipped-panel behavior.

The comparison passes in development, Release and ASan/UBSan. All 46 CTests pass, and private-window checks exercise the external view transitions and telemetry strip alongside cockpit restoration and paused-frame retention.


### Infrared and night-view palette selection

```sh
python3 tools/check_palette_selection.py
python3 tools/check_environment_palettes.py
python3 tools/check_window_palettes.py
```

The original selector now owns its normal-palette dirty flag and infrared latch. The designator requests infrared directly. Missile nose view tests the original active-projectile-list condition independently of weapon guidance type. Night vision also checks the environment/night/request flags and preserves the original exclusions for particular external/transition views. Repeated requests suppress redundant uploads; a changed normal palette stays pending while infrared is displayed.

**5,952 native selector updates agree** across all 29 views, every eligibility combination, dirty/infrared initial state and persistent switching sequences. The original selection tail executes unmodified with its saved-register stack supplied; hardware upload is observed at its external boundary. Altitude, flashes, blackout/redout generation and full session ordering remain separate work. Another **441 compact native cases** run without game assets in CTest.

Lighting configuration now owns the five authored altitude palette names/boundaries, infrared palette, schematic and night status independently of terrain loading. All bindings agree with **33 independently captured native environment parses**. Keeping this separate also permits checking configurations whose names are not valid standalone terrain grids. Live flight uses these infrared bindings for missile/designator views and Shift+N night vision, including normal-colour restoration in the original excluded cameras. Private-window tests exercise Shift+N, day/night eligibility, chase-view exclusion and cockpit restoration, checking the displayed colours against the actual palette banks.

Development, Release and ASan/UBSan selector/configuration comparisons pass. All 47 development CTests pass. Complete scene lighting/remaps, altitude palette progression, weather and complete-frame/session equivalence remain open renderer gates.

All 128 retail missions also run 1,024 simulation steps and draw under ASan/UBSan after the lighting-configuration separation.


### Altitude palettes, protected colours and the VGA DAC

```sh
python3 tools/check_palette_lighting.py
python3 tools/check_dac_upload.py
python3 tools/check_window_palettes.py
```

The live world palette now follows the original five altitude banks and boundaries. Native `0x73214` selects a bank pair from the negated camera-anchor Y, retaining integer 50-stage blending, truncated divisions, the shared cached step and target-view exclusion. The fixed-colour overlay retains its pitch/roll phase, executable-backed colour entries and magenta leave-unchanged sentinel. These phases use the original player pitch/roll inputs separately from the camera altitude. Live startup also retains the original black first palette entry.

The flash/redout/blackout palette painters preserve their native retained flash byte, update gates, byte wrapping and effect-sample requests. The original blackout branch's second sample threshold reads the redout word; this quirk is kept. **4,224 original updates agree in every palette byte, retained step/phase/flash value and effect request across all 33 environments**, including boundary heights, repeated state, target view, reserved colours, disabled effects, signed effect levels and high-bit HUD values. Original startup and complete palette helpers execute; authored banks and view/effect state are supplied. The check stops before the separately verified upload selector. Darkside planet blending and the controllers which produce flash/blackout/redout state remain outside this comparison; live flight currently binds the altitude/fixed-colour path, rather than inventing those effect triggers.

Tracing the upload also corrected an earlier research interpretation of `HUDCOL`. It is the green component of palette entry 6, with a compiled value of 125 and original Y/U clamp of 90–127. Native `0xc770c` uploads these bytes unchanged; the six-bit VGA DAC discards their high two bits. Live palette expansion therefore models DAC masking, while external palette files still reject components greater than 63. The native differential uploader and a six-bit port model agree with C++ RGB presentation for **304 updates and 227,352 component writes**, including all byte values, the HUD range and repeated unchanged palettes. Another 26 compact native DAC cases run without original assets in CTest and retain strict asset-file validation.

Y/U now change brightness at the original flight-input cadence and preserve the native dirty-palette request even when both keys cancel each other. Private-window checks observe the default green level and both clamps in the displayed HUD, alongside night-vision/camera palette handoffs. Atmospheric geometry, weather, colour remaps, effect-state producers and complete world-frame/session equivalence remain separate work.

The palette and DAC comparisons pass in development, Release and ASan/UBSan. All 48 development CTests pass. All 128 retail missions run 1,024 simulation steps and draw under sanitizers with the new live palette path.


### Temporary BINGO and PULL UP HUD warnings

```sh
python3 tools/check_hud_alerts.py
python3 tools/check_target_tracking.py --alerts
```

The temporary HUD line tables previously described as launch notices are the authored **BINGO** and **PULL UP** messages. Their owned state retains the selected shape and original 108-tick timer. A request replaces the current shape and restarts that timer. Each actual draw subtracts its supplied elapsed word, with wrapping before the signed expiry test; a skipped HUD draw does not consume time. The original painter sends direct VGA lines without clipping, so comparison offsets are restricted to valid physical-screen positions. Changing the line viewport does not clip these messages.

**512 complete original frames agree in pixels, written coverage, selected message and retained timer**, covering both shapes, the fuel threshold and adjacent doubles, repeated/no draws, requests, valid offsets, ignored viewports, expiry and long-tick wrapping. The original BINGO request executes before the failed/intermittent HUD gate and uses the executable-backed fuel threshold of 500. The native unsafe out-of-screen line-write context is excluded explicitly.

Another **1,024 complete original forward-HUD frames agree** with warning requests, paint order and timer included alongside all existing target/lock animation and event checks. NAV paints its warning inside its own layout, before the outer brake/chute message repeat; AA/AG paint it at the end. Refuelling contact selection and terrain-risk producers remain separate. Live flight now supplies low fuel before its HUD-fault gate and elapsed ticks to the painter. The PULL UP shape/request/painter is verified, while its actual terrain-risk trigger still needs its native selecting consumer.

The warning painter and full-composition comparisons pass in development, Release and ASan/UBSan. All 48 CTests and private-window camera/pause checks pass. All 128 retail missions run 1,024 simulation steps and draw under sanitizers after the live BINGO integration.


### Aerial refuelling and tanker HUD

```sh
python3 tools/check_refuelling.py
python3 tools/check_view_cameras.py --refuelling
python3 tools/check_target_tracking.py --alerts --navigation
python3 tools/check_window_refuelling.py --data-dir /path/to/TFX
```

The original apostrophe handler now opens/closes the player aircraft's refuelling equipment, saves the current NAV/AA/AG mode and forces NAV until it restores the saved mode. The camera-stage controller searches the fifty allied slots for the nearest eligible tanker, retaining original tie order and wrapped distance arithmetic. Alignment, reconnect delay, speed gates, port anchors and coupling divisors follow native `0x94efc`, `0x94e34` and `0x950f4`. The original coupling moves the tanker towards the player's port. Refuelling adds the executable's 14 fuel units per player update, caps at aircraft capacity and requests the original afterburner warning. Connected refuelling inhibits cannon and carried-store release and selects the corresponding aircraft model entries.

**6,144 persistent original-code updates agree** in all controller state, target selection, tanker poses, exact fuel bits and emitted requests. The cases cover all three aircraft and reach 46 connections from approach, with 882 coupled frames and 1,289 tanker updates. Original controller, bearing, anchor and distance code executes. SSD category lookup is supplied from separately checked resource semantics; model-entry, audio and voice requests are observed at their external boundaries. Fuel transfer executes its original player-update prefix before the camera controller, preserving the previous phase's lifetime. These checks do not establish complete flight-session ordering or collision protection.

The camera comparison also agrees across **11,776 updates in 23 modes with four supplied refuelling phases**, preserving the original phase addition to player model entries. The live tanker HUD now draws its direction cue, telemetry and marker before weapon acquisition, sharing the retained projected point and sight. This optional path consumes its own BINGO/PULL UP warning draw before the later weapon layout. **1,024 complete original composed HUD frames agree** in pixels, coverage, target/lock state, warning timers and events with this contact path enabled. Sensor/render lifetime ordering outside this supplied sequence remains a separate gate.

Controller, camera and HUD comparisons pass in development, Release and ASan/UBSan. Private-window checks exercise real apostrophe input, forced NAV, saved AA/AG restoration, pause and camera return. All 48 CTests pass. The complete 128-mission sanitizer pass still advances 1,024 steps per mission and draws. Live sample/voice playback awaits the audio backend; ILS, automatic landing and non-Arcade flight models remain separate work.


### Instrument landing system

```sh
python3 tools/check_landing.py --selection
python3 tools/check_landing.py
python3 tools/check_target_tracking.py --alerts --navigation --landing
python3 tools/check_window_landing.py --data-dir /path/to/TFX
```

I/backslash now uses the original ILS toggle, including its inhibition gates, NAV selection, control-setting results and damage-dependent voice request. The destination selector checks the player route's last point, then its first. It accepts a runway SSD at that cell or searches allied surface slots in descending order for an eligible carrier. Actor retirement and the carrier SSD's destroyed state are distinct checks. Destroyed-carrier and missing-runway messages retain their native order. Landing ports use the first three initialized SSD custom words; the approach beacon uses the original integer movement helper and 20,480-unit setback.

**1,536 complete original key/selection executions agree**, including all three aircraft, ordinary/realistic control coefficients, gates, empty routes, missing runways, destroyed carriers, exact control-setting bits and voice/radio requests. The native waypoint accessor and surface enumerator execute. Terrain handles, initialized SSD port/type/damage fields and audio requests are declared external boundaries. This comparison includes 252 runway and 654 carrier selections; it does not claim a complete native world-load/session trace.

The HUD first directs the player to the beacon, then computes the original lateral and vertical corrections for runway approach. The retained corrections and height status follow actual HUD draws. Land-based offsets use the native extended-precision product and truncation; carriers retain their authored offsets. **1,024 complete native guidance frames agree** in every pixel, written coverage, state word, projected-point input and radio request. They include 308 beacon-to-runway transitions and directed high, low and aligned approaches. The world-point projector is supplied at its independently verified boundary. A compact set of **61 original state captures** runs in CTest without game assets.

The combined forward-HUD comparison also agrees across **1,024 complete frames** with targets, refuelling contacts, BINGO/PULL UP warnings and ILS enabled together. It checks the original removal of NAV/ammunition labels, guidance placement, warning timing and retained landing state. Live flight binds original route data and SSD custom fields to this path. Private-window checks exercise both keys, forced NAV, subsequent weapon modes, pause and external-view return. Automatic landing, remaining flight-model consumers of the returned control coefficients and the autopilot's speed/altitude request producer are still separate work; audio requests await playback.

The ILS controller, complete guidance and combined HUD comparisons pass in development, Release and ASan/UBSan. All 49 CTests pass. All 128 retail missions also advance 1,024 steps and draw under sanitizers after integration.


### Automatic campaign return after flight

```sh
python3 tools/check_campaign_return.py --data-dir /path/to/TFX
```

Native launcher `0x72588` resumes its caller after the flight loop, result processing, FINISH and teardown; it has no extra diagnostic results wait. Campaign flight now returns as soon as FINISH completes, allowing the existing parser to select its original result, recovery, life-loss and next-mission presentations. Direct `--mission` launches retain their standalone diagnostic results page.

A private-window integration check restores a disposable native-format pilot into the final Arcade mission with one life, uses the original arming screen, reaches aircraft loss through normal real-time simulation and observes the automatic return to the authored Arcade presentation. No damage, result or FINISH variables are injected. Shift+Q then exits the presentation normally. This tests the assembled return path; the original parser/rule subsystem comparisons remain its independent evidence, rather than a claim of complete native session equivalence.
