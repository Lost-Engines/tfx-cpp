cmake_minimum_required(VERSION 3.30)
project(tfx VERSION 0.1.0 LANGUAGES CXX)
include(CTest)
include(cmake/dependencies.cmake)

function(configure_first_party target)
  target_compile_features(${target} PUBLIC cxx_std_26)
  target_include_directories(${target} PUBLIC "${PROJECT_SOURCE_DIR}/src" "${PROJECT_SOURCE_DIR}")
  set_target_properties(${target} PROPERTIES CXX_EXTENSIONS OFF CXX_SCAN_FOR_MODULES OFF)
  target_compile_options(${target} PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion;-ffp-contract=off>
    $<$<AND:$<CONFIG:RelWithDebInfo>,$<CXX_COMPILER_ID:GNU,Clang,AppleClang>>:-UNDEBUG>
  )
endfunction()

add_library(tfx_core
  src/cockpit/auxiliary.cpp
  src/cockpit/auxiliary.h
  src/cockpit/warnings.cpp
  src/cockpit/warnings.h
  src/cockpit/mfd.cpp
  src/cockpit/mfd.h
  src/cockpit/instrument_assets.cpp
  src/cockpit/instrument_assets.h
  src/cockpit/readouts.cpp
  src/cockpit/readouts.h
  src/presentation/drawing.cpp
  src/presentation/drawing.h
  src/planning/review.cpp
  src/planning/review.h
  src/planning/notes.cpp
  src/planning/notes.h
  src/planning/map_view.cpp
  src/planning/map_view.h
  src/presentation/widget_font.cpp
  src/presentation/widget_font.h
  src/resources/compiled_overlay.cpp
  src/resources/compiled_overlay.h
  src/resources/compiled_panel.cpp
  src/resources/compiled_panel.h
  src/planning/document.cpp
  src/planning/document.h
  src/presentation/score_player.cpp
  src/presentation/score_player.h
  src/presentation/scores.cpp
  src/presentation/scores.h
  src/presentation/arming_preview.cpp
  src/presentation/arming_preview.h
  src/presentation/arming_screen.cpp
  src/presentation/arming_screen.h
  src/presentation/arming_widgets.cpp
  src/presentation/arming_widgets.h
  src/presentation/arming_controller.cpp
  src/presentation/arming_controller.h
  src/presentation/arming_assets.cpp
  src/presentation/arming_assets.h
  src/presentation/frontend.cpp
  src/presentation/frontend.h
  src/presentation/pilot_panel.cpp
  src/presentation/pilot_panel.h
  src/presentation/pilots.cpp
  src/presentation/pilots.h
  src/presentation/save.cpp
  src/presentation/save.h
  src/presentation/menu_player.cpp
  src/presentation/menu_player.h
  src/presentation/cursor.cpp
  src/presentation/cursor.h
  src/presentation/menu.cpp
  src/presentation/menu.h
  src/presentation/session.cpp
  src/presentation/session.h
  src/presentation/player.cpp
  src/presentation/player.h
  src/presentation/timing.cpp
  src/presentation/timing.h
  src/presentation/text.cpp
  src/presentation/text.h
  src/presentation/fonts.cpp
  src/presentation/fonts.h
  src/presentation/program.cpp
  src/presentation/program.h
  src/presentation/runtime.cpp
  src/presentation/runtime.h
  src/resources/media.cpp
  src/resources/media.h
  src/actors/surface_combat.cpp
  src/actors/surface_combat.h
  src/sensors/ground.cpp
  src/sensors/ground.h
  src/actors/contact_region.cpp
  src/actors/contact_region.h
  src/actors/scenery.cpp
  src/actors/scenery.h
  src/missions/progress.cpp
  src/missions/progress.h
  src/flight/damage.cpp
  src/flight/damage.h
  src/sensors/air.cpp
  src/sensors/air.h
  src/weapons/loadout.cpp
  src/weapons/loadout.h
  src/weapons/cannon.cpp
  src/weapons/cannon.h
  src/weapons/runtime.cpp
  src/weapons/runtime.h
  src/weapons/projectile.cpp
  src/weapons/projectile.h
  src/weapons/definition.cpp
  src/weapons/definition.h
  src/actors/manoeuvre.cpp
  src/actors/manoeuvre.h
  src/actors/air.cpp
  src/actors/air.h
  src/actors/air_motion.cpp
  src/actors/air_motion.h
  src/actors/program.cpp
  src/actors/program.h
  src/actors/surface.cpp
  src/actors/surface.h
  src/flight/arcade.cpp
  src/flight/arcade.h
  src/math/attitude.cpp
  src/math/attitude.h
  src/flight/aircraft.h
  src/flight/airframes.cpp
  src/flight/airframes.h
  src/flight/stores.cpp
  src/flight/stores.h
  src/missions/timeline.cpp
  src/missions/timeline.h
  src/missions/rules.cpp
  src/missions/rules.h
  src/missions/initialisation.cpp
  src/missions/initialisation.h
  src/simulation/timing.cpp
  src/simulation/timing.h
  src/resources/executable_tables.cpp
  src/resources/executable_tables.h
  src/render/framebuffer.cpp
  src/render/framebuffer.h
  src/render/camera.cpp
  src/render/camera.h
  src/render/sprites.cpp
  src/render/sprites.h
  src/render/software_renderer.cpp
  src/render/software_renderer.h
  src/math/native.cpp
  src/math/native.h
  src/models/shape.cpp
  src/models/shape.h
  src/world/instance.cpp
  src/world/instance.h
  src/world/collision.cpp
  src/world/collision.h
  src/world/animation.cpp
  src/world/animation.h
  src/world/scene.cpp
  src/world/scene.h
  src/world/environment.cpp
  src/world/environment.h
  src/world/definition.cpp
  src/world/definition.h
  src/world/assets.cpp
  src/world/assets.h
  src/resources/archive.cpp
  src/resources/archive.h
  src/resources/binary.h
  src/resources/ra.cpp
  src/resources/ra.h
)
target_compile_definitions(tfx_core PUBLIC VECTORSTORM_NO_BOOST)
configure_first_party(tfx_core)

add_executable(tfx
  src/main.cpp
  src/platform/arming.cpp
  src/platform/arming.h
  src/platform/flight.cpp
  src/platform/flight.h
  src/platform/presentations.cpp
  src/platform/presentations.h
  src/platform/window.cpp
  src/platform/window.h
)
target_link_libraries(tfx PRIVATE tfx_core PRIVATE glfw PRIVATE OpenGL::GL)
configure_first_party(tfx)

if(BUILD_TESTING)
  add_executable(hud_font_probe tests/hud_font_probe.cpp)
  target_link_libraries(hud_font_probe PRIVATE tfx_core)
  configure_first_party(hud_font_probe)

  add_executable(widget_font_probe tests/widget_font_probe.cpp)
  target_link_libraries(widget_font_probe PRIVATE tfx_core)
  configure_first_party(widget_font_probe)

  add_executable(planning_tests tests/planning_test.cpp)
  target_link_libraries(planning_tests PRIVATE tfx_core)
  configure_first_party(planning_tests)
  add_test(NAME planning.native_document_layout_and_bounds COMMAND planning_tests)

  add_executable(planning_probe tests/planning_probe.cpp)
  target_link_libraries(planning_probe PRIVATE tfx_core)
  configure_first_party(planning_probe)

  add_executable(score_probe tests/score_probe.cpp)
  target_link_libraries(score_probe PRIVATE tfx_core)
  configure_first_party(score_probe)

  add_executable(score_tests tests/score_test.cpp)
  target_link_libraries(score_tests PRIVATE tfx_core)
  configure_first_party(score_tests)
  add_test(NAME presentation.native_high_score_storage COMMAND score_tests)

  add_executable(pilot_probe tests/pilot_probe.cpp)
  target_link_libraries(pilot_probe PRIVATE tfx_core)
  configure_first_party(pilot_probe)

  add_executable(name_probe tests/name_probe.cpp)
  target_link_libraries(name_probe PRIVATE tfx_core)
  configure_first_party(name_probe)

  add_executable(save_tests tests/save_test.cpp)
  target_link_libraries(save_tests PRIVATE tfx_core)
  configure_first_party(save_tests)
  add_test(NAME presentation.native_save_layout_and_bounds COMMAND save_tests)

  add_executable(save_probe tests/save_probe.cpp)
  target_link_libraries(save_probe PRIVATE tfx_core)
  configure_first_party(save_probe)

  add_executable(cursor_probe tests/cursor_probe.cpp)
  target_link_libraries(cursor_probe PRIVATE tfx_core)
  configure_first_party(cursor_probe)

  add_executable(menu_probe tests/menu_probe.cpp)
  target_link_libraries(menu_probe PRIVATE tfx_core)
  configure_first_party(menu_probe)

  add_executable(menu_tests tests/menu_test.cpp)
  target_link_libraries(menu_tests PRIVATE tfx_core)
  configure_first_party(menu_tests)
  add_test(NAME presentation.menu_scripts_and_clicks COMMAND menu_tests)

  add_executable(player_tests tests/player_test.cpp)
  target_link_libraries(player_tests PRIVATE tfx_core)
  configure_first_party(player_tests)
  add_test(NAME presentation.scene_phases_and_caption_input COMMAND player_tests)

  add_executable(player_probe tests/player_probe.cpp)
  target_link_libraries(player_probe PRIVATE tfx_core)
  configure_first_party(player_probe)

  add_executable(presentation_timing_probe tests/presentation_timing_probe.cpp)
  target_link_libraries(presentation_timing_probe PRIVATE tfx_core)
  configure_first_party(presentation_timing_probe)
  add_test(NAME presentation.native_input_waits_animation_fades COMMAND presentation_timing_probe ${PROJECT_SOURCE_DIR}/tests/reference/presentation_timing.txt)

  add_executable(text_clock_probe tests/text_clock_probe.cpp)
  target_link_libraries(text_clock_probe PRIVATE tfx_core)
  configure_first_party(text_clock_probe)
  add_test(NAME presentation.native_reveal_clock COMMAND text_clock_probe ${PROJECT_SOURCE_DIR}/tests/reference/text_clock.txt)

  add_executable(text_tests tests/text_test.cpp)
  target_link_libraries(text_tests PRIVATE tfx_core)
  configure_first_party(text_tests)
  add_test(NAME presentation.native_text_boundaries COMMAND text_tests)

  add_executable(text_probe tests/text_probe.cpp)
  target_link_libraries(text_probe PRIVATE tfx_core)
  configure_first_party(text_probe)

  add_executable(font_tests tests/font_test.cpp)
  target_link_libraries(font_tests PRIVATE tfx_core)
  configure_first_party(font_tests)
  add_test(NAME presentation.font_tables_and_coverage COMMAND font_tests)

  add_executable(font_probe tests/font_probe.cpp)
  target_link_libraries(font_probe PRIVATE tfx_core)
  configure_first_party(font_probe)

  add_executable(presentation_tests tests/presentation_test.cpp)
  target_link_libraries(presentation_tests PRIVATE tfx_core)
  configure_first_party(presentation_tests)
  add_test(NAME presentation.control_flow_and_boundaries COMMAND presentation_tests)

  add_executable(presentation_probe tests/presentation_probe.cpp)
  target_link_libraries(presentation_probe PRIVATE tfx_core)
  configure_first_party(presentation_probe)

  add_executable(media_tests tests/media_test.cpp)
  target_link_libraries(media_tests PRIVATE tfx_core)
  configure_first_party(media_tests)
  add_test(NAME resources.native_media_boundaries COMMAND media_tests)

  add_executable(media_probe tests/media_probe.cpp)
  target_link_libraries(media_probe PRIVATE tfx_core)
  configure_first_party(media_probe)

  add_executable(surface_combat_probe tests/surface_combat_probe.cpp)
  target_link_libraries(surface_combat_probe PRIVATE tfx_core)
  configure_first_party(surface_combat_probe)
  add_test(NAME actors.native_surface_combat COMMAND surface_combat_probe ${PROJECT_SOURCE_DIR}/tests/reference/surface_combat.txt)

  add_executable(ground_probe tests/ground_probe.cpp)
  target_link_libraries(ground_probe PRIVATE tfx_core)
  configure_first_party(ground_probe)
  add_test(NAME sensors.native_ground_geometry_and_selection COMMAND ground_probe ${PROJECT_SOURCE_DIR}/tests/reference/ground_sensors.txt)

  add_executable(world_contacts_probe tests/world_contacts_probe.cpp)
  target_link_libraries(world_contacts_probe PRIVATE tfx_core)
  configure_first_party(world_contacts_probe)
  add_test(NAME world.native_fixed_placements_and_surface_region COMMAND world_contacts_probe ${PROJECT_SOURCE_DIR}/tests/reference/world_contacts.txt)

  add_executable(death_probe tests/death_probe.cpp)
  target_link_libraries(death_probe PRIVATE tfx_core)
  configure_first_party(death_probe)
  add_test(NAME missions.native_player_loss_transition COMMAND death_probe ${PROJECT_SOURCE_DIR}/tests/reference/death.txt)

  add_executable(credit_probe tests/credit_probe.cpp)
  target_link_libraries(credit_probe PRIVATE tfx_core)
  configure_first_party(credit_probe)
  add_test(NAME missions.native_air_and_mobile_credit COMMAND credit_probe ${PROJECT_SOURCE_DIR}/tests/reference/credit.txt)

  add_executable(progress_probe tests/progress_probe.cpp)
  target_link_libraries(progress_probe PRIVATE tfx_core)
  configure_first_party(progress_probe)
  add_test(NAME missions.native_target_progress_and_termination COMMAND progress_probe ${PROJECT_SOURCE_DIR}/tests/reference/progress.txt)

  add_executable(damage_probe tests/damage_probe.cpp)
  target_link_libraries(damage_probe PRIVATE tfx_core)
  configure_first_party(damage_probe)
  add_test(NAME flight.native_system_damage_and_repair COMMAND damage_probe ${PROJECT_SOURCE_DIR}/tests/reference/damage.txt)

  add_executable(sensors_probe tests/sensors_probe.cpp)
  target_link_libraries(sensors_probe PRIVATE tfx_core)
  configure_first_party(sensors_probe)
  add_test(NAME sensors.native_air_radar_and_seeker COMMAND sensors_probe ${PROJECT_SOURCE_DIR}/tests/reference/sensors.txt)

  add_executable(attachment_tests tests/attachment_test.cpp)
  target_link_libraries(attachment_tests PRIVATE tfx_core)
  configure_first_party(attachment_tests)
  add_test(NAME models.carried_store_context_and_bounds COMMAND attachment_tests)

  add_executable(auxiliary_probe tests/auxiliary_probe.cpp)
  target_link_libraries(auxiliary_probe PRIVATE tfx_core)
  configure_first_party(auxiliary_probe)

  add_executable(warning_probe tests/warning_probe.cpp)
  target_link_libraries(warning_probe PRIVATE tfx_core)
  configure_first_party(warning_probe)

  add_executable(overlay_tests tests/overlay_test.cpp)
  target_link_libraries(overlay_tests PRIVATE tfx_core)
  configure_first_party(overlay_tests)
  add_test(NAME resources.compiled_overlay_bounds COMMAND overlay_tests)

  add_executable(overlay_probe tests/overlay_probe.cpp)
  target_link_libraries(overlay_probe PRIVATE tfx_core)
  configure_first_party(overlay_probe)

  add_executable(mfd_probe tests/mfd_probe.cpp)
  target_link_libraries(mfd_probe PRIVATE tfx_core)
  configure_first_party(mfd_probe)

  add_executable(readout_probe tests/readout_probe.cpp)
  target_link_libraries(readout_probe PRIVATE tfx_core)
  configure_first_party(readout_probe)

  add_executable(sprite_probe tests/sprite_probe.cpp)
  target_link_libraries(sprite_probe PRIVATE tfx_core)
  configure_first_party(sprite_probe)

  add_executable(arming_preview_probe tests/arming_preview_probe.cpp)
  target_link_libraries(arming_preview_probe PRIVATE tfx_core)
  configure_first_party(arming_preview_probe)

  add_executable(arming_controls_probe tests/arming_controls_probe.cpp)
  target_link_libraries(arming_controls_probe PRIVATE tfx_core)
  configure_first_party(arming_controls_probe)

  add_executable(arming_screen_probe tests/arming_screen_probe.cpp)
  target_link_libraries(arming_screen_probe PRIVATE tfx_core)
  configure_first_party(arming_screen_probe)

  add_executable(airframe_probe tests/airframe_probe.cpp)
  target_link_libraries(airframe_probe PRIVATE tfx_core)
  configure_first_party(airframe_probe)

  add_executable(arming_probe tests/arming_probe.cpp)
  target_link_libraries(arming_probe PRIVATE tfx_core)
  configure_first_party(arming_probe)
  add_test(NAME weapons.native_mount_permissions_and_assignment COMMAND arming_probe --check ${CMAKE_CURRENT_SOURCE_DIR}/tests/reference/arming.txt)

  add_executable(loadout_probe tests/loadout_probe.cpp)
  target_link_libraries(loadout_probe PRIVATE tfx_core)
  configure_first_party(loadout_probe)
  add_test(NAME weapons.native_pylons COMMAND loadout_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/loadout.txt)

  add_executable(cannon_probe tests/cannon_probe.cpp)
  target_link_libraries(cannon_probe PRIVATE tfx_core)
  configure_first_party(cannon_probe)
  add_test(NAME weapons.native_keyboard_cannon COMMAND cannon_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/cannon.txt)

  add_executable(anchor_probe tests/anchor_probe.cpp)
  target_link_libraries(anchor_probe PRIVATE tfx_core)
  configure_first_party(anchor_probe)
  add_test(NAME weapons.native_anchor_transform COMMAND anchor_probe ${PROJECT_SOURCE_DIR}/tests/reference/anchor.txt)

  add_executable(projectile_runtime_probe tests/projectile_runtime_probe.cpp)
  target_link_libraries(projectile_runtime_probe PRIVATE tfx_core)
  configure_first_party(projectile_runtime_probe)

  add_executable(contact_tests tests/contact_test.cpp)
  target_link_libraries(contact_tests PRIVATE tfx_core)
  configure_first_party(contact_tests)
  add_test(NAME weapons.native_contact_damage COMMAND contact_tests ${PROJECT_SOURCE_DIR}/tests/reference/contact.txt)

  add_executable(projectile_probe tests/projectile_probe.cpp)
  target_link_libraries(projectile_probe PRIVATE tfx_core)
  configure_first_party(projectile_probe)
  add_test(NAME weapons.native_projectile_motion COMMAND projectile_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/projectile.txt)

  add_executable(air_combat_tests tests/air_combat_test.cpp)
  target_link_libraries(air_combat_tests PRIVATE tfx_core)
  configure_first_party(air_combat_tests)
  add_test(NAME actors.native_air_combat COMMAND air_combat_tests ${PROJECT_SOURCE_DIR}/tests/reference/air_combat.txt)
  add_test(NAME actors.native_air_death COMMAND air_combat_tests ${PROJECT_SOURCE_DIR}/tests/reference/air_death.txt --death)

  add_executable(air_tests tests/air_test.cpp)
  target_link_libraries(air_tests PRIVATE tfx_core)
  configure_first_party(air_tests)
  add_test(NAME actors.native_air_sequences COMMAND air_tests ${PROJECT_SOURCE_DIR}/tests/reference/air.txt)

  add_executable(air_probe tests/air_probe.cpp)
  target_link_libraries(air_probe PRIVATE tfx_core)
  configure_first_party(air_probe)

  add_executable(air_motion_probe tests/air_motion_probe.cpp)
  target_link_libraries(air_motion_probe PRIVATE tfx_core)
  configure_first_party(air_motion_probe)
  add_test(NAME actors.native_air_motion COMMAND air_motion_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/air_motion.txt)

  add_executable(timeline_probe tests/timeline_probe.cpp)
  target_link_libraries(timeline_probe PRIVATE tfx_core)
  configure_first_party(timeline_probe)
  add_test(NAME missions.native_timeline_sequences COMMAND timeline_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/timeline.txt)

  add_executable(world_probe tests/world_probe.cpp)
  target_link_libraries(world_probe PRIVATE tfx_core)
  configure_first_party(world_probe)

  add_executable(instance_tests tests/instance_test.cpp)
  target_link_libraries(instance_tests PRIVATE tfx_core)
  configure_first_party(instance_tests)
  add_test(NAME world.native_instance_events COMMAND instance_tests)

  add_executable(instance_probe tests/instance_probe.cpp)
  target_link_libraries(instance_probe PRIVATE tfx_core)
  configure_first_party(instance_probe)

  add_executable(collision_tests tests/collision_test.cpp)
  target_link_libraries(collision_tests PRIVATE tfx_core)
  configure_first_party(collision_tests)
  add_test(NAME world.native_collision_boundaries COMMAND collision_tests)

  add_executable(tfx_tests tests/resource_test.cpp)
  target_link_libraries(tfx_tests PRIVATE tfx_core)
  configure_first_party(tfx_tests)
  add_test(NAME resources.malformed_and_literal COMMAND tfx_tests)

  add_executable(animation_tests tests/animation_test.cpp)
  target_link_libraries(animation_tests PRIVATE tfx_core)
  configure_first_party(animation_tests)
  add_test(NAME actors.native_animation_boundaries COMMAND animation_tests)

  add_executable(timing_tests tests/timing_test.cpp)
  target_link_libraries(timing_tests PRIVATE tfx_core)
  configure_first_party(timing_tests)
  add_test(NAME simulation.native_timing_boundaries COMMAND timing_tests)

  add_executable(tfx_replay tests/replay.cpp)
  target_link_libraries(tfx_replay PRIVATE tfx_core)
  configure_first_party(tfx_replay)

  add_executable(mission_tests tests/mission_test.cpp)
  target_link_libraries(mission_tests PRIVATE tfx_core)
  configure_first_party(mission_tests)
  add_test(NAME missions.native_initialisation_boundaries COMMAND mission_tests)

  add_executable(rules_tests tests/rules_test.cpp)
  target_link_libraries(rules_tests PRIVATE tfx_core)
  configure_first_party(rules_tests)
  add_test(NAME missions.native_result_boundaries COMMAND rules_tests)

  add_executable(stores_tests tests/stores_test.cpp)
  target_link_libraries(stores_tests PRIVATE tfx_core)
  configure_first_party(stores_tests)
  add_test(NAME flight.native_store_contributions COMMAND stores_tests)
  set_tests_properties(flight.native_store_contributions PROPERTIES SKIP_RETURN_CODE 77)

  add_executable(stores_probe tests/stores_probe.cpp)
  target_link_libraries(stores_probe PRIVATE tfx_core)
  configure_first_party(stores_probe)

  add_executable(rules_probe tests/rules_probe.cpp)
  target_link_libraries(rules_probe PRIVATE tfx_core)
  configure_first_party(rules_probe)

  add_executable(mission_probe tests/mission_probe.cpp)
  target_link_libraries(mission_probe PRIVATE tfx_core)
  configure_first_party(mission_probe)

  add_executable(surface_tests tests/surface_test.cpp)
  target_link_libraries(surface_tests PRIVATE tfx_core)
  configure_first_party(surface_tests)
  add_test(NAME actors.native_surface_sequences COMMAND surface_tests ${PROJECT_SOURCE_DIR}/tests/reference/surface.txt)

  add_executable(actor_probe tests/actor_probe.cpp)
  target_link_libraries(actor_probe PRIVATE tfx_core)
  configure_first_party(actor_probe)

  add_executable(attitude_probe tests/attitude_probe.cpp)
  target_link_libraries(attitude_probe PRIVATE tfx_core)
  configure_first_party(attitude_probe)

  add_executable(arcade_probe tests/arcade_probe.cpp)
  target_link_libraries(arcade_probe PRIVATE tfx_core)
  configure_first_party(arcade_probe)
  add_test(NAME flight.native_arcade_sequences COMMAND arcade_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/arcade.txt)
  add_test(NAME flight.native_disabled_sequences COMMAND arcade_probe --check-disabled ${PROJECT_SOURCE_DIR}/tests/reference/disabled.txt)
  add_test(NAME flight.native_ground_sequences COMMAND arcade_probe --check-ground ${PROJECT_SOURCE_DIR}/tests/reference/ground_flight.txt)
  set_tests_properties(flight.native_arcade_sequences flight.native_ground_sequences PROPERTIES SKIP_RETURN_CODE 77)

  add_executable(tfx_probe tests/probe.cpp)
  target_link_libraries(tfx_probe PRIVATE tfx_core)
  configure_first_party(tfx_probe)
endif()
