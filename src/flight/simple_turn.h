#pragma once

#include "math/attitude.h"
#include "simulation/timing.h"

namespace tfx::flight {

struct simple_turn_state {
  math::attitude orientation{};
  float heading_remainder{0};
  int16_t bank_correction{0};
  float turn_response{0};
  float movement_per_tick{0};
  float coordinated_turn_rate{0};
  float metres_per_second{0};
  float g_load{0};
};
struct simple_turn_context {
  float mach{0};
  float pitch_rate{0};
  simulation::timer_ticks elapsed{0};
};

// Native 0x8d3cc: bank compensation and coordinated turn, followed by speed/G stores.
void update_simple_turn(simple_turn_state &state, simple_turn_context const &context);

} // namespace tfx::flight
