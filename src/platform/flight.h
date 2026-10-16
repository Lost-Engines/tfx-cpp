#pragma once

#include "missions/rules.h"
#include "platform/window.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "simulation/timing.h"

namespace tfx::platform {

struct flight_options {
  std::string mission{"miss501"};
  std::string environment{}, grid{};
  std::optional<vec2<unsigned int>> cell{};
  std::optional<std::filesystem::path> screenshot{};
  unsigned int scale{0}, scene_radius{6}, frame_limit{0}, flight_steps{0};
  simulation::flight_model model{simulation::flight_model::arcade};
  bool inspect{false};
};
// True means FINISH ran and the caller may resume its authored campaign graph.
bool fly_mission(resources::archive const &game, resources::executable_tables const &tables,
  flight_options const &options, missions::variables &campaign, window *shared_window = nullptr);

} // namespace tfx::platform
