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

  add_executable(rules_probe tests/rules_probe.cpp)
  target_link_libraries(rules_probe PRIVATE tfx_core)
  configure_first_party(rules_probe)

  add_executable(mission_probe tests/mission_probe.cpp)
  target_link_libraries(mission_probe PRIVATE tfx_core)
  configure_first_party(mission_probe)

  add_executable(tfx_probe tests/probe.cpp)
  target_link_libraries(tfx_probe PRIVATE tfx_core)
  configure_first_party(tfx_probe)
endif()
