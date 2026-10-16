#pragma once

#include "actors/program.h"

namespace tfx::actors {

struct scenery_placement {
  unsigned int record;
  uint16_t profile_id;
  std::string definition;
  vec3<int32_t> position;
  uint16_t event;
};
std::vector<scenery_placement> initialise_scenery(program const &source, std::span<profile const> profiles);

} // namespace tfx::actors
