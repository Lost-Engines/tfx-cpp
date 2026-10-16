#pragma once

#include <string>
#include <vector>
#include "actors/program.h"

namespace tfx::actors {

enum class surface_action : uint8_t { route, retired, dead, normal, waiting };
enum class surface_flag : uint16_t { destroyed = 0x0800, retired = 0x1000 };
enum class surface_request_kind { nearby_targets, ground_target, radio };
struct surface_request {
  surface_request_kind kind;
  vec2<int16_t> cell{0,0};
  uint16_t weapon{0};
  std::string text{};
};
struct surface_state {
  initial_actor pose;
  resources::bytes commands;
  unsigned int cursor{0};
  int16_t heading_rate{0};
  int32_t acceleration{0};
  int16_t input_ticks{0};
  int16_t wait_seconds{0};
  uint32_t actions{0};
};

surface_state create_surface(initial_actor const &actor, program const &source);
std::vector<surface_request> advance_surface(surface_state &state, profile const &profile);

} // namespace tfx::actors
