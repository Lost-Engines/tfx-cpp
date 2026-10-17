# Remaining implementation plan

Reference: September 1994 TFX 2.05. The project remains a native C++26 reconstruction using original installation data and the existing software-rendering/window approach. CD music remains deferred, and CI remains unconfigured.

The executable starts the original introduction, enrolment and menus, with DOS-compatible pilot save/load, briefing/review/arming and authored results handoff. All four player flight models, keyboard/mouse/joystick acquisition, autopilot, recovery, refuelling and automatic landing are connected. Aircraft and surface routes/combat, carried stores, sensors, damage, mission rules, cockpit displays and cameras also run. Backtick now opens the original configuration/realism dialogs with live settings and compatible preference saving. Complete audio device/trigger integration, complete campaign/session coverage, remaining collision/sensor details and exact world-renderer/weather fidelity remain unfinished. See [implementation.md](implementation.md) for verification boundaries.

The aim is to reach a substantially complete, automatically exercised game before requesting interactive review. The order below brings the largest uncertainties—runtime timing, aerodynamics and context-dependent callbacks—into the early work. Each increment should include its verification and be committed independently.

## Progress

The native game now connects pilot enrolment and persistence, original presentations and menus, mission review and arming, all four flight models, moving aircraft and surface actors, weapons and damage, mission results, scores and campaign returns. All 128 retail setups have C++ simulation/render coverage. A naturally played training engagement also completes targeting, missile release, a kill, FINISH, debriefing and the next-hop handoff with inherited flight/campaign state. Complete campaign-path coverage remains a separate gate.

Cockpit/HUD instruments, sensors, all camera controllers, scenery animation/collision, original model detail and queue ordering, textures, shadows, palettes, weather, horizon and precipitation are connected. Subsystem comparisons execute the original code at declared boundaries. All 128 retail missions now match the original launch and first sixteen Arcade frames in all captured state and every indexed pixel: 2,048 complete frames. Mission 501 also agrees through 256 neutral Arcade frames, with separate controlled targeting, combat and recording comparisons. Longer combat traces are now checking scores, objective counters and termination countdowns as well as movement/rendering state.

FM, LAPC-I and Sound Canvas music use the original OSL drivers through DBOPL, Munt and Nuked Sound Canvas. Standard sampled Sound Blaster effects/speech and the original flight music/cue selection are connected. Gravis's separate auxiliary path, optional QSound processing and complete-session audio coverage remain open. CD music is deferred as requested.

Alt+V recording and automatic post-flight WNN/replay are connected. The original format has byte-exact writer/reader comparisons; nineteen replay frames and their palettes agree pixel for pixel. A private-window campaign test records a complete successful training flight, observes both WNN introductions and replay, then continues to the next mission. The original filename editor now supports case-sensitive typing, backspace, scrolling, its 18-character limit and Enter; 115 complete original widget frames agree. All 195 asset-free regressions pass in development, Release and ASan/UBSan.

The wider retail-session sweep found and corrected launch fuel ordering: physical initialisation consumes the previous pylon inventory before new stores are fitted. Mission 604 now matches sixteen complete original frames in all four flight models, and a landed tank-equipped launch matches its first-frame refill. A successful recorded training flight also verifies inventory retention into the next mission. Rotated/near-clipped model lines now have 1,024 complete original-program comparisons.

The immediate work is to resolve the cannon command and later drawing differences exposed by longer controlled combat traces, then continue outcome and campaign paths. Remaining audio paths and older sprite-backed drawing retain explicit verification gates. No interactive checkpoint is required for these analytical and automated checks. Commands and detailed evidence are in [implementation.md](implementation.md) and [recording.md](recording.md).

The numbered sections below retain the implementation sequence and its verification boundaries.

## 1. Establish complete-session reference capture

The paused M-key tactical map is connected, including regional artwork,
route/contact telemetry, target/runway blinking and normal-palette handoff
from infrared flight. Its complete painter/state comparison covers 1,920
original frames. Private-window input checks cover pause preservation,
consumed dismissal keys and the infrared return. Both maps now bind the ILS
runway marker; surface contact enumeration excludes destroyed, retired and
neutral actors as the original does. Flight recording, filename editing and
post-flight WNN/replay are connected and independently compared with the
original. The 4-key ILBM capture, slash afterburner
stop, keypad cockpit-height controls and held keypad throttle controls are
also connected. Twelve complete screenshot files match the original encoder
byte for byte; 24-frame Arcade and Realistic shortcut sequences match every
captured state and pixel. The original right-Shift PLOP dispatcher is also
connected, with 4,096 original input comparisons, a complete 20-frame
activation/deactivation comparison and a private-window check. Cheat-enabled
in-flight rearming is connected, including the paused custom-fit screen and
immediate DEFAULT_WEAPONS branch. The persistent held-key poller now matches all 16,384
combinations, including modifier/automatic-landing retention. Orbit, roll,
distance, Ctrl chase translation and keypad steering are connected; 32-frame
Simple and Realistic sequences match all captured state and pixels. Arcade
now uses the original relative-mouse steering without invented arrow motion.
Cheat Ctrl+D rearming is connected too, with the original immediate branch for
DEFAULT_WEAPONS missions. Inventory changes now refresh flight mass, drag and
tank metadata; the inventory binding agrees in 1,197 original store cases.
Real mouse automation places a tank, restores defaults and checks live physical
metadata, paused physics and consumed Escape. A 24-frame immediate-refit session
also matches all original captured state and pixels. Recording and remaining
view/designator bindings are the next control work.

Extend the relocated-original-code harness from isolated calls to reproducible initialisation/update sequences. Where complete DOS context is necessary, instrument scripted runs of the original through DOSBox. Original runs should use disposable writable installations so they do not alter the user's configuration or pilots.

Record the mission and inherited campaign state, controls, timer increments, random seeds, relevant configuration, actor identities, callback selection and observable state changes. Retain separate clock domains for the simulation, SSD animation, presentation BIOS/retrace timing and music. Replaying recorded elapsed intervals must preserve the native update order, clamping, backlog and projectile subdivision rules.

Build a headless C++ session runner that accepts the same inputs and reports the first divergent tick and field. Compare logical actor identities rather than allocator addresses. Start with a correctly initialised flight session and add longer traces as subsystems become available.

**Completion gate:** a repeatable native initialisation/update trace and an initial C++ comparison path for implemented state, with every stub or external input declared. Expected results must come from the original or independent evidence; successful execution alone does not establish agreement.

## 2. Implement mission initialisation and live world state

Expand the current literal scene selection into native mission setup: starts, angles, speed, inherited aircraft, loadout, weather and initial actors. Implement the shared expression/control-flow machinery needed by initialisation, then the SSD runtime's custom storage, conditional initialisers, event dispatch, changing draw assemblies, animation replacement, collision queries and destruction lifecycle. Live combat/sensor predicates are completed in step 6.

Give each live instance its own state and handles while sharing immutable definitions and resources. Preserve native creation/update/removal order, deferred or immediate event behaviour, random consumption and handle reuse. The present repeatable tile-variant preview must be replaced with the actual initialiser-driven sequence.

**Completion gate:** compare world/actor initialisation, parameters, random states and event effects with original execution, including repeated creation, damage and removal. All 128 retail-associated mission setups should run through the real initialisation path.

## 3. Reconstruct player flight and controls

Trace and translate the complete player callback chain, starting from the three captured aircraft presets. Establish coefficient meanings, units and initialisation dependencies from their consumers. Cover the native flight-model settings, control scaling, engines, fuel, carried-store mass/drag/moments, configuration changes, ground contact, takeoff, landing, stall/recovery and refuelling behaviour where present.

The aerodynamics use x87 calculations. Capture the FPU precision/rounding environment and intermediate storage boundaries; neither `double` nor `long double` can be assumed to reproduce them automatically on every target. Use independent original-session checkpoints to check the isolated emulator's numerical results. Any tolerance needs a reason and must preserve later branch decisions, converted poses and collision outcomes.

Feed recorded keyboard/mouse/joystick states through a common control-state boundary. Keep the original input semantics and sample/update timing; host device access should supply those inputs without becoming part of the physics.

**Completion gate:** repeatable multi-step trajectories for Eurofighter, F-117 and F-22 under neutral flight, control changes, different stores/fuel and representative boundary conditions. Check both internal numerical state and the integer pose handed to the world renderer. This stage can produce flyable diagnostic builds without requiring user playtesting.

## 4. Complete the native renderer and cockpit composition

Replace inspection approximations with the original camera transforms, clipping, projection, detail selection, visibility rules and world/actor ordering. Finish exact raster boundaries, textured remapping, lighting/palette selection, weather, horizon and effects. Preserve the palette-index operations and native drawing quirks.

Translate the compiled cockpit overlays and implement HUD/MFD drawing from declared telemetry, including radar, navigation, stores, warnings and secondary scene cameras. Bind available flight state here; bind live sensor/combat results as those systems arrive in step 6. Retain the virtual cockpit's authored static MFD textures. Its dynamic replacements belong to a later enhanced version. Trace actual selecting callers for the 29 viewport records before assigning camera modes.

**Completion gate:** compare complete controlled frames and palette uploads, not just polygon interiors. Cover each aircraft/camera, near-plane crossings, distant detail changes, day/night/twilight, representative weather, terrain edges, stores and effects. Visual differences should produce pixel/coverage diagnostics tied to the responsible stage.

## 5. Implement moving actors and AI

Implement the runtime meanings of the 47 entity profiles, aircraft groups, surface units, formations, spawning and retirement. Execute compiled waypoint commands and CBN manoeuvres with their real timing and eligibility conditions. Resolve the conditional operands and callback relationships that the inspection viewers currently retain without executing.

**Completion gate:** compare multi-update actor state, route branches, radio events, formations and manoeuvre choices using declared player trajectories and random seeds. Exercise aircraft, ground units and ships, plus spawn/despawn and damaged-state transitions. Recovered command layouts alone are insufficient for this gate.

## 6. Join sensors, weapons, damage and mission rules

Implement radar/target acquisition and selection, weapon release conditions, all used guidance callbacks and timed stages, countermeasures, swept collision and damage responses. Connect projectile contacts to the appropriate SSD events, effects and actor bookkeeping.

Execute the mission expression language, completion/failure conditions, scoring, friendly/unauthorised-target rules, FINISH/END actions and results returned to the campaign graph. Named completion variables must be driven by the actual combat/event path.

Use FWS Hop 1, mission 501, as the first complete combat slice: correct inherited aircraft/setup, the one-on-one MiG engagement, timed message, enemy loss, completion and score/result handoff. Expand to intercepts, ground attacks, friendly-fire/court-martial cases and other authored mission classes.

**Completion gate:** original/C++ agreement on trajectories, acquisition, hit events, damage transitions, target counts, score and mission result. Distinguish tests that inject a rare state from sessions that reach it through normal controls and combat; both are useful, but prove different things.

## 7. Restore the original front end and persistent progression

Implement saved parser graph execution, variables, branches, subroutine calls and graph changes. Add native menus, pilots/enrolment, training unlocks, campaigns, briefing/debriefing, waypoint planning and loadout selection. Reconstruct configuration and pilot persistence from the native readers/writers, preserving compatibility where verified.

Port the image/sprite/font and animation/presentation paths with their native reveal, fade, wait, skip and language behaviour. Drive their variables and text substitutions from real session state. Connect the in-flight configuration menu and original view/input commands to the live systems.

**Completion gate:** script menu and presentation interactions, compare graph/variable state and screenshots, and test save/reload/continue against the original. Exercise training eligibility, success, failure, death and court-martial branches. Entry through the normal front end and direct diagnostic mission launch must produce equivalent flight state when given equivalent inputs.

## 8. Integrate synthesised music and sampled sound

Implement TFX's OSL sequencing and original device/event behaviour, reusing the verified FM, LA and Sound Canvas hardware backends where appropriate. Keep TFX's own uploads, arrangements and device behaviour when reusing those backends. Compare register/MIDI/SysEx output and timing with the existing native captures. Respect runtime selection, retained preselection, pause/reset, the shared game clock and game volume; the research auditions use different volume settings in some cases.

Implement sampled effects, radio speech, looping, pitch, panning, priorities and their runtime triggers. Bind flight, combat, damage and presentation events to the mixer. Optional synthesiser ROMs remain external user assets.

**Completion gate:** compare event streams and reproducible PCM, including repeated track changes, controller resets, overlapping effects and varied audio callback sizes. Playback must follow live game state rather than a prerecorded listening export. CD playback remains deferred.

## 9. Complete corpus coverage and prepare interactive review

Broaden end-to-end replay coverage throughout the work, then finish a coverage matrix across the 128 retail-associated missions, three playable aircraft, five regional worlds, flight-model/realism settings, weather, languages and relevant campaign outcomes. Parse and account for all 201 stored mission sources (128 retail-associated and 73 other retained scripts) while keeping retained/unlinked material distinct from confirmed retail flow.

Select representative interacting scenarios rather than blindly multiplying every setting. Include long sessions, timer wrapping, resource reuse, repeated save/load, focus loss and audio restarts. Diagnose unsupported callbacks or unexpected states with the mission, tick and actor context; each essential unsupported path should fail its verification case explicitly.

Run sanitizers and profile Release on repeatable scenes. Check desktop behaviour on the available platforms, keeping the established floating-window and scaling behaviour. Prepare a minimal native package and clear startup help without adding CI.

**Completion gate:** the ordinary front-end-to-flight-to-result/save path works; representative missions complete through real simulated actions; every claimed comparison is reproducible; remaining gaps and intentional omissions are listed explicitly.

## Interactive review boundary

The intended first requested playtest is a usable integrated build: pilot selection, original briefing/planning/loadout, a complete training engagement, working flight/cockpit/HUD/sound, debrief and save/continue. By then, automated work should also cover the other player aircraft and representative campaign scenarios.

User review should concentrate on control feel and usability, audiovisual cohesion, and behaviour that differs from our coverage. Rare encounters and difficult original-game situations should be reproduced through instrumented scenarios on the implementation side.

The exact stopping point cannot be guaranteed in advance. The highest-risk unknowns are the full x87 update chain and callbacks whose behaviour depends on broad game state. If original traces disagree, investigate and reduce the discrepancy before asking the user to judge it by eye. Request interactive assistance only for a specific remaining question that the analytical/original-execution checks cannot answer, with a prepared reproduction and a clear observation to make.

## Evidence and storage discipline

Maintain separate labels for decoded data, isolated native comparisons, complete native-session comparisons, and inspection/inferred behaviour. Keep compact input/state/event fixtures and hashes in the repository. Generate bulk frame/audio captures in ignored scratch space and retain a capture only when it adds distinct evidence.

Current evidence is indexed in [implementation.md](implementation.md). The sibling research tree's `analysis/game-logic.md`, `compiled-programs.md`, `weapons-and-dynamics.md`, `campaign-flow.md`, `configuration.md`, `cockpits.md`, `lighting.md` and `audio/README.md` identify the native entry points and existing captures on which this plan builds.


The view/night palette selector now also has 5,952 native state comparisons and live infrared/night-vision bindings. All 33 authored environment palette configurations are independently checked, including their five altitude banks/boundaries. Altitude/fixed-colour palette generation is now separately checked in 4,224 complete native updates, and VGA DAC upload/expansion in 304 updates. Live altitude colours and Y/U HUD intensity are connected. G-force, flak-flash and sunlight-glare producers now have native comparisons and live bindings. Full scene lighting, sky and weather remain separate renderer increments.


Temporary BINGO/PULL UP HUD messages now have 512 complete native painter/state comparisons and 1,024 composed forward-HUD comparisons. Live low-fuel requests retain the original fault gate and paint cadence. PULL UP terrain-risk detection and the remaining approach/navigation consumers are still separate increments.

Aerial refuelling now has 6,144 persistent native controller/fuel comparisons and live hookup controls, tanker movement, fuel transfer, model events and contact HUD. Camera phase additions agree in all 11,776 dispatcher cases, and contact HUD composition agrees in 1,024 complete frames. The private-window check verifies mode save/restore, pause and view return. ILS, automatic recovery, remaining collision/refuelling caller context and audio consumers remain separate increments.

ILS destination selection and guidance are now connected to I/backslash. There are 1,536 native selection/key cases, 1,024 complete guidance frames, 61 asset-free state fixtures and 1,024 combined forward-HUD frames including ILS. Private-window input/pause/view-return checks pass. Automatic landing, non-Arcade control consumers, the autopilot's approach-speed request producer and audio remain open.

Campaign flight now returns automatically after FINISH, restoring the authored presentation flow without the direct-launch diagnostic results pause. A private-window check reaches aircraft loss through real-time simulation and resumes the original Arcade life-loss presentation from a disposable DOS pilot. Complete outcome/campaign coverage, ejection and the original in-flight quit/options interaction remain open.

The ejected-pilot physics kernel now has 12,288 exact native state/event comparisons, and its shared float-to-fixed down-axis builder agrees in 4,096 native cases across the pilot and camera copies. There are 262 compact asset-free fixtures for these two components. Live Escape, animation/actor ownership, abandoned-aircraft motion, camera and recovery/outcome consumers remain to be connected.


Authored area flak now has 8,192 complete original frame comparisons across 16
persistent day/night scenarios, including its dedicated random generator,
height/cloud/region gates, 20-slot pool and drawing range. Live daytime bursts,
nighttime models, audio/radio, white palette flash and cockpit shake are
connected. Sun glare is also connected; full renderer equivalence remains open. All 33
environments retain their original cloud-layer height, offset and grid name.


Authored SSD secondary blasts now feed the live effect pool through synchronous
placed requests. All 782 corpus requests have native placement coverage, and a
controlled real factory's collision/animation/draw emission agrees with the
original. Shared smoke trails, legacy offsets and ground shadows remain.


Live SSD drawing/animation now binds its range and anchor queries to the player
reference, independently of camera selection. The shared placed-anchor query
has 11,320 complete original comparisons; all 128 mission scenes also survive
64 integrated steps after the binding change. Full renderer eligibility and
whole-session comparisons remain open.


Shared missile smoke now uses the original 200-slot pool and ten-unit sampling,
with complete original segment, pool and post-motion dispatch comparisons.
Camera bounding-volume visibility is independently checked, and a controlled
private-window test verifies the live smoke path without replacing visibility.
Sky/weather and complete world-renderer eligibility remain open.


The original sun/lightning producers and one-shot lightning palette consumer
are connected, with 16,384 complete original cases. Upper cloud scenery now
uses the native frame's base/upper-grid selection and camera anchor, including
height equality. The original banded horizon and precipitation remain next.


The original altitude/bank-dependent horizon replaces the flat flight backdrop.
Its complete projected surfaces, integer clipping/scan conversion and full VGA
frames have native comparisons. Moving ground phase and the actual camera draw
eligibility/height handoffs are also connected and checked through complete
camera/player controllers. Precipitation and general world raster/lighting
remain next.


Original storm rain now paints after the world and beneath the cockpit, with
native pixel, field/RNG, wind-drift and complete main-frame gate comparisons.
Weather-to-rain shared random ordering is checked across all 33 environments;
mission startup now separates that retained stream from the later terrain
reset. General world raster/lighting, visibility-conditioned animation and
whole-session equivalence remain open.


Missile-nose aperture now follows the original driver reset/change through
model projection, bounding-volume visibility and horizon painting. Both modes,
complete controller handoffs and the live firing/camera/result path have
native or private-window coverage. General polygon coverage and near-plane
clipping, textures/remaps, lighting and visibility-conditioned animation remain.


Flat untextured model faces beyond the near plane now use native integer
screen clipping and scan conversion, with complete original VGA comparisons.
Explicit camera bounds carry the actual cockpit and MFD rectangles. Near
crossings and shaded/patterned/textured coverage remain separate next steps.


Flat model near-plane crossings now use the original word-depth midpoint
search, Q16 replay, clipped projection and integer raster, with complete native
edge and VGA-frame comparisons. The model-facing bytecode fallback, general
shaded/patterned/textured drawing and full-scene transforms/order remain open.


Original model-facing bytecode now distinguishes projected dword determinants,
near-vertex 3D plane tests and the raster's word-difference winding. Native
camera units reach the interpreter callback. Complete converted synthetic
model programs agree in control flow and VGA pixels; full actor transforms,
distance remap selection, general shading/textures and scene order remain.


Original distance remaps now load from the game's root colour table and bind
to actual integer/fixed assembly submission depth. Flat and Gouraud model
faces share native integer clipping and edges, including their distinct
near-plane attribute interpolation. Complete converted model programs agree
through both paths. General patterned/textured/rounded edges, full actor
transforms, animation visibility eligibility and global scene order remain.


Native model metrics now select the authored polygon level and distant
one/two-pixel representations. SSD drawing retains assembly, integer-anchor
and fixed-anchor caches and their bounding-sphere admission. Complete
queued multi-level model frames agree with original VGA output. Full actor
transforms, immediate/queued ordering, queue overflow and animation visibility
eligibility remain separate work alongside patterned/textured/rounded edges.


The original bounded queue, tie ordering and full-queue replacement now have
complete original allocation/order comparisons and live scene bindings.
Queued parameters are owned snapshots. Immediate submissions, ground shadows,
animation eligibility, renderer-phase scheduling and full actor transforms
remain separate gates, along with patterned/textured/rounded coverage.


Complete-frame headless coverage now includes update, composition and
frame-tail decisions in the interactive order. All retail missions pass
64 frames in every flight model; sanitizers repeat the full mission corpus.
Longer neutral flights exercise real loss/FINISH and retained render state.
These supplied-input C++ runs complement the isolated original comparisons;
original complete-session traces and successful campaign coverage remain.


Unrounded patterned model faces now share the verified integer near clipping
and edge table. All nine pattern/logical modes agree through complete VGA
frames and procedural states, including their sparse endpoint/phase rules
and the original narrow-span line-stipple quirk. Rounded/textured edges,
full actor transforms, shadows and complete scene scheduling remain open.


Outer model transforms now retain native Euler addition, normal/special SSD
orientation rules, signed cache scaling, Q15 view/body matrix stores and the
actual submitted camera cache. All six constructors have angle/size captures;
complete converted absolute-vertex programs agree in basis words and VGA
frames. Model-local articulation/matrix stacks, shadows, immediate delivery
and complete scene scheduling remain independent gates.


Ground-shadow requests now retain their native height eligibility, shared
ground plane, fixed camera cache, queue entry, quantised flattening and forced
black model drawing. Original placement and complete flat/Gouraud silhouette
frames agree, and a normal landed mission reaches the production draw path.
Immediate delivery, renderer-phase scheduling and model-local articulation
remain separate work alongside rounded/textured edge fidelity.


Immediate SSD draws now use their native scratch slot and retain per-instruction
part snapshots. Persistent slot size/type metadata, mutable cache scaling and
the separate retained parameter bank have complete mixed native sequence
comparisons, including capacity and frame resets. Direct converted-model
frames agree too. Remaining renderer work includes visibility-conditioned
animation, complete phase scheduling, model-local articulated matrices and
rounded/textured boundaries.

Visibility-dependent model animation now follows the original unconditional,
visible and frozen constructors, including per-viewport jitter and the main
camera's integer versus fixed player submission. Original comparisons cover
8,192 animation calls, 16,384 viewport resets and 12,288 camera updates.
Model-local articulated transforms, rounded/textured boundaries and complete
world phase order remain the next renderer gaps.

Live model-local articulation now uses native Q15 camera matrices, wrapped
vertex products and scoped anchors, with complete original frames covering
nested rotated helpers and carried stores. The shared player loadout table is
also connected to live model drawing. Rounded/textured boundaries and full
world phase/session comparisons remain open; the independent inspection view
continues to use its continuous transforms.

Rounded model surfaces now have complete original projection/midpoint/corner,
patterned pixel and procedural-state comparisons over 1,024 frames. Sparse
skipped-row termination and empty-byte procedural consumption also retain their
native rules, with another 2,048 patterned/near-clipped frames unchanged.
Remaining model material-state operations and texture boundaries are next.

Authored fixed-palette model effects now retain row-zero lookup, ink reuse and
helper persistence, with 1,024 complete original model frames and live crash
painter observation. Parameter-selected drawing state, specialised retained
helpers and general texture edge/near-plane fidelity remain separate work.

Original affine model textures now retain integer projection, unsigned Q7 UV
near clipping, signed-word viewport clipping, biased edges, Q24 pixel stepping
and mapped transparency. Complete original comparisons cover 1,024 screen-space
frames, 1,024 ordinary/near-clipped model frames and 8,192 UV intersections;
shared Gouraud clipping remains unchanged. All 164 regressions and every retail
mission pass development/sanitizer coverage, and a private-window observer
confirms real retail-atlas texels reach the production painter. Parameter-selected
materials, specialised lighting helpers and full session/phase equivalence remain.

Scoped helper depth palettes and vertex-selected condition distance now execute
instead of being silently omitted. Complete original frame comparisons also
establish the distinct flat/Gouraud rules for crossed projected edges; ordinary,
varied-depth and texture paths retain separate regressions. Parameter-selected
constant ink/mode controls and complete world/session scheduling remain next.

Parameter-selected constant ink/modes and their separate restoration now execute
through the live native model path, including projection-dependent shaded/texture
consumer changes. Plain rounded quads and standalone rounded arcs reach their
proper consumers. Complete original model programs and 4,096 supplied-span frames
establish the distinct dense/sparse/logical edge rules. All 172 regressions and
the full retail mission corpus pass in development and sanitizers. Point/line
precision, older sprite-backed model drawing and full phase/session comparison
remain separate gates.

Authored dot/disc primitives now use the shared native dispatch, including
signed-word projection, the distinct one/two-pixel viewport rules, high-depth
radius scaling, wide-view radius retention and material/pattern state. Original
complete programs cover all circle sizes and retain the partial-circle
corner-clipping quirk. All 174 regressions pass in development, Release and
sanitizers; every retail mission and private-window effects/controls pass.
Native lines, legacy sprite-backed model drawing and full phase/session
comparison remain separate work.

The laser-designator placeholder is replaced by its original full-screen
viewport, integer camera, projected reticle sprite and flashing T/L indicators.
Complete native search/tracking controller/overlay comparisons cover gimbals,
zoom, camera caches/matrices, projection, pixels, coverage and blink state;
normal private-window input reaches each live consumer and returns to flight.
Complete world/session scheduling and acquisition context remain independent
gates, alongside native line precision and legacy sprite-backed models.


Complete native-session capture now executes real launch, DEFAULT/DONE arming,
player/AI updates, camera, world/HUD composition and frame-tail events. Every
frame is checked, with radio requests and procedural state observed separately.
Arcade mission 501 agrees on its observed state through 256 frames; Simple
through 64, and both advanced flight models through 32. The F-22 also agrees on
every pixel through 16 frames. Landed F-117 startup, AWACS speech/ticker,
advanced HUD readouts, actor admission and original sky submission are now
connected. Remaining whole-frame differences and broader controlled-input /
combat / campaign sessions remain explicit gates.
