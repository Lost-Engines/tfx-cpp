# Remaining implementation plan

Reference: September 1994 TFX 2.05. The project remains a native C++26 reconstruction using original installation data and the existing software-rendering/window approach. CD music remains deferred, and CI remains unconfigured.

The executable starts the original introduction, enrolment and menus, with DOS-compatible pilot save/load, briefing/review/arming and authored results handoff. All four player flight models, keyboard/mouse/joystick acquisition, autopilot, recovery, refuelling and automatic landing are connected. Aircraft and surface routes/combat, carried stores, sensors, damage, mission rules, cockpit displays and cameras also run. Backtick now opens the original configuration/realism dialogs with live settings and compatible preference saving. Complete synthesised audio, complete campaign/session coverage, remaining collision/sensor details and exact world-renderer/weather fidelity remain unfinished. See [implementation.md](implementation.md) for verification boundaries.

The aim is to reach a substantially complete, automatically exercised game before requesting interactive review. The order below brings the largest uncertainties—runtime timing, aerodynamics and context-dependent callbacks—into the early work. Each increment should include its verification and be committed independently.

## Progress

The complete outer player callback agrees across 324 retained fields in 4,608 frames over 48 scenes, including warm manual/autopilot handovers. A second 4,608-frame run additionally changes flight models in flight, covering original model-entry conversions, body/display matrix sharing and frame-tail measurement. Each numerical stage and scripted landing path retains its independent original-execution checks. All 128 retail missions have also advanced 1,024 steps in each of the four models and rendered their resulting scene.

Original configuration readers/writer, joystick and mouse adapters, G-force redout/blackout and authored cloud/storm wind/temperature selection are connected. The original option dialogs have complete pixel/state comparisons and private-window interaction checks; return to enrolment follows the original pilot-selection path. Standard sampled Sound Blaster playback and its menu switch are connected. Synthesised music and auxiliary OSL effects remain in progress.

The initial timing increment is complete: a bounded relocated-original harness and headless C++ runner agree on 4,096 controlled frame sequences, including timer wrapping/poll consumption, exact stored float/double bits, previous-frame animation gating and projectile subdivision. External timer inputs and unimplemented projectile callbacks are declared. The original mission-script loader also agrees with C++ INIT declarations for all 128 retail scripts in fresh and seeded prior state (256 setups). All 128 retail FINISH programs also agree in 8,192 supplied result-state cases, including native scoring and parser quirks. Carried-store flight effects also match all stored bits in 1,197 native loadouts; their current arithmetic backend is limited to an x87-precision host format. Player attitude and 4,608 multi-step Arcade flight states now also match original execution across the three aircraft, including stall/ceiling recovery and afterburner; 9,216 ground-start/takeoff steps also match with supplied contacts and automatic recovery disabled. All 192 compiled actor programs also match native initialisation (3,572 individual actors), and 104,320 surface-controller updates plus 90,000 synthetic boundary updates agree in the declared noncombat context. SSD instances now also agree across 19,589 persistent-state captures and 4,800 complete native terrain queries. Aircraft waypoint/formation execution now also matches 352,896 ticks without ground targets and 1,411,584 ticks with supplied intact targets; combat decisions now also agree over 2,823,168 updates, with another full-corpus fatal-hit/lifecycle comparison. The original 98-slot projectile pool, mutual contact damage and cannon branch now have native checks and live integration. Moving-object collision, the complete SSD lifecycle, combat outcomes, caller context and complete-session traces remain outstanding; these increments do not satisfy the complete-session gate. See [timing evidence](implementation.md#simulation-timing-and-headless-replay).

The original presentation graph, media/font/text paths, scene timing and options-menu scripts now have native checks and a window host. All 372 retail visual nodes are exercised (592 language cases); individual presentations/menus can be launched without entering flight. Pilot creation/load/replacement, native slot persistence, training eligibility, enrolment-to-flight dispatch and campaign-variable return are now connected. The original high-score table, storage and Arcade log/return actions are also integrated, with complete native screen-frame comparisons. Remaining result consumers and complete campaign-path verification remain.

Original arming is now integrated between the normal briefing/review and flight. Its screen uses the dedicated aircraft models, original store masks and exclusion rules, paired mounting, native SSD mount picking, loadout statistics, bay animations and palette ramps. Custom pointer flows run for all three aircraft, and private-window tests enter live training through custom arming and the original DONE button. Original widget, controller, picking, camera and ramp comparisons are detailed in the implementation notes. Complete native 3D-frame equivalence and remaining modal/input-wait details are still separate verification work.

Cockpit reconstruction now has verified shared sprite/mask painters, clock/fuel/throttle/countermeasure readouts, and seven MFD page painters. Complete original pixel/coverage comparisons cover eighteen sprite banks, embedded masks, all aircraft and both outer displays; native page selection and text measurement are checked independently. Warning/auxiliary indicators, both radar views, all regional moving maps and per-viewport clipping now also have complete native frame/state comparisons. Scene-camera/control pages, full viewport composition and live flight integration remain in progress.

The original readouts, eight instrument MFD pages, both radars, moving maps, warning/auxiliary lamps and scene-camera requests now have native comparisons and live flight bindings. Original display cycling, fuel-range smoothing and paused-frame retention are connected; private X11 tests exercise every display. The default cockpit frame, upper flight readings, heading/pitch scales and NAV/AA/AG weapon layouts are also connected, including cannon/Mk82 prediction. Radio scrolling/replay and selected-target telemetry, heading/direction cues, acquisition/lock blinking and ground-designation outlines are connected too. The original head-turn, chase, fixed fly-past, tactical, target-observer and virtual/target-tracking camera controllers are connected, including queued transitions and model selection. Navigation/approach cues, recovery/ejection views, complete impact-observer lifetimes, remaining camera artwork and flight-system inputs still need integration. Whole-frame and whole-session fidelity remain open gates.

## 1. Establish complete-session reference capture

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

Implement TFX's OSL sequencing and original device/event behaviour, reusing the verified FM, LA and Sound Canvas hardware backends where appropriate. Keep TFX's own uploads, arrangements and device behaviour when reusing those backends. Compare register/MIDI/SysEx output and timing with the existing native captures. Respect runtime selection, retained preselection, pause/reset, changing song clocks and game volume; the research auditions use different volume settings in some cases.

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


The view/night palette selector now also has 5,952 native state comparisons and live infrared/night-vision bindings. All 33 authored environment palette configurations are independently checked, including their five altitude banks/boundaries. Altitude/fixed-colour palette generation is now separately checked in 4,224 complete native updates, and VGA DAC upload/expansion in 304 updates. Live altitude colours and Y/U HUD intensity are connected. Flash/blackout painters are verified with supplied state; their producers, full scene lighting and weather remain separate renderer increments.


Temporary BINGO/PULL UP HUD messages now have 512 complete native painter/state comparisons and 1,024 composed forward-HUD comparisons. Live low-fuel requests retain the original fault gate and paint cadence. PULL UP terrain-risk detection and the remaining approach/navigation consumers are still separate increments.

Aerial refuelling now has 6,144 persistent native controller/fuel comparisons and live hookup controls, tanker movement, fuel transfer, model events and contact HUD. Camera phase additions agree in all 11,776 dispatcher cases, and contact HUD composition agrees in 1,024 complete frames. The private-window check verifies mode save/restore, pause and view return. ILS, automatic recovery, remaining collision/refuelling caller context and audio consumers remain separate increments.

ILS destination selection and guidance are now connected to I/backslash. There are 1,536 native selection/key cases, 1,024 complete guidance frames, 61 asset-free state fixtures and 1,024 combined forward-HUD frames including ILS. Private-window input/pause/view-return checks pass. Automatic landing, non-Arcade control consumers, the autopilot's approach-speed request producer and audio remain open.

Campaign flight now returns automatically after FINISH, restoring the authored presentation flow without the direct-launch diagnostic results pause. A private-window check reaches aircraft loss through real-time simulation and resumes the original Arcade life-loss presentation from a disposable DOS pilot. Complete outcome/campaign coverage, ejection and the original in-flight quit/options interaction remain open.

The ejected-pilot physics kernel now has 12,288 exact native state/event comparisons, and its shared float-to-fixed down-axis builder agrees in 4,096 native cases across the pilot and camera copies. There are 262 compact asset-free fixtures for these two components. Live Escape, animation/actor ownership, abandoned-aircraft motion, camera and recovery/outcome consumers remain to be connected.
