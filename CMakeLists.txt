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
  src/platform/window.cpp
  src/platform/window.h
)
target_link_libraries(tfx PRIVATE tfx_core PRIVATE glfw PRIVATE OpenGL::GL)
configure_first_party(tfx)

if(BUILD_TESTING)
  add_executable(projectile_probe tests/projectile_probe.cpp)
  target_link_libraries(projectile_probe PRIVATE tfx_core)
  configure_first_party(projectile_probe)
  add_test(NAME weapons.native_projectile_motion COMMAND projectile_probe --check ${PROJECT_SOURCE_DIR}/tests/reference/projectile.txt)

  add_executable(air_combat_tests tests/air_combat_test.cpp)
  target_link_libraries(air_combat_tests PRIVATE tfx_core)
  configure_first_party(air_combat_tests)
  add_test(NAME actors.native_air_combat COMMAND air_combat_tests ${PROJECT_SOURCE_DIR}/tests/reference/air_combat.txt)

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
  add_test(NAME flight.native_ground_sequences COMMAND arcade_probe --check-ground ${PROJECT_SOURCE_DIR}/tests/reference/ground_flight.txt)
  set_tests_properties(flight.native_arcade_sequences flight.native_ground_sequences PROPERTIES SKIP_RETURN_CODE 77)

  add_executable(tfx_probe tests/probe.cpp)
  target_link_libraries(tfx_probe PRIVATE tfx_core)
  configure_first_party(tfx_probe)
endif()
