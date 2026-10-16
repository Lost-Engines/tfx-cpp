#pragma once

#include "platform/window.h"
#include "presentation/session.h"
#include "resources/executable_tables.h"

namespace tfx::platform {
void play_presentation(resources::archive const &game, resources::executable_tables const &tables,
  std::string const &name, std::string_view function, std::string const &language,
  unsigned int scale, unsigned int frame_limit, std::optional<std::filesystem::path> const &screenshot);
} // namespace tfx::platform
