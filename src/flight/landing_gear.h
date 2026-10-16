#pragma once

#include <vector>
#include "flight/damage.h"

namespace tfx::flight {

struct landing_gear_state {
  bool down{false};
  system_condition condition{system_condition::normal};
  float vertical_speed{0};
};
struct landing_gear_context {
  int16_t forward_y{0};
  float metres_per_second{0};
  bool landed{false};
  bool previous_landed{false};
  double airborne_speed_limit{0};
  double ground_speed_limit{0};
  double touchdown_descent_limit{0};
};

// Native 0x8d7ec. Audio requests retain order, including two warnings in one update.
std::vector<unsigned int> update_landing_gear(landing_gear_state &state, landing_gear_context const &context);

} // namespace tfx::flight
