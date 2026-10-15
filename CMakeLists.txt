cmake_minimum_required(VERSION 3.28)
project(tfx VERSION 0.1.0 LANGUAGES CXX)
include(CTest)
include(cmake/dependencies.cmake)

function(configure_first_party target)
  target_compile_features(${target} PUBLIC cxx_std_23)
  target_include_directories(${target} PUBLIC "${PROJECT_SOURCE_DIR}/src" "${PROJECT_SOURCE_DIR}")
  set_target_properties(${target} PROPERTIES CXX_EXTENSIONS OFF CXX_SCAN_FOR_MODULES OFF)
  target_compile_options(${target} PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall;-Wextra;-Wpedantic;-Wconversion>
    $<$<AND:$<CONFIG:RelWithDebInfo>,$<CXX_COMPILER_ID:GNU,Clang,AppleClang>>:-UNDEBUG>
  )
endfunction()

add_library(tfx_core
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

  add_executable(tfx_probe tests/probe.cpp)
  target_link_libraries(tfx_probe PRIVATE tfx_core)
  configure_first_party(tfx_probe)
endif()
