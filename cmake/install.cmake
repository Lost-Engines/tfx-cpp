# The portable distribution contains only the executable and platform helpers.
install(TARGETS tfx RUNTIME DESTINATION . COMPONENT Runtime)
if(WIN32)
  install(DIRECTORY scripts DESTINATION . USE_SOURCE_PERMISSIONS COMPONENT Runtime
    PATTERN "*.sh" EXCLUDE)
  install(CODE [[
    file(GLOB_RECURSE scripts
      "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/scripts/*.bat"
      "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/scripts/*.txt")
    foreach(script IN LISTS scripts)
      file(READ "${script}" contents)
      string(REPLACE "\r\n" "\n" contents "${contents}")
      string(REPLACE "\n" "\r\n" contents "${contents}")
      file(WRITE "${script}" "${contents}")
    endforeach()
  ]] COMPONENT Runtime)
else()
  install(DIRECTORY scripts DESTINATION . USE_SOURCE_PERMISSIONS COMPONENT Runtime
    PATTERN "*.bat" EXCLUDE)
endif()
