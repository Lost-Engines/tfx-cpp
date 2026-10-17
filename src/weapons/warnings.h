#pragma once

#include <optional>
#include "math/native.h"
#include "simulation/timing.h"

namespace tfx::weapons {

struct warning_state {
  int16_t cooldown{0};
  uint16_t incoming{0};
};
struct projectile_warning {
  unsigned int sample;
  bool music{false};
};

void begin_warning_step(warning_state &state, simulation::timer_ticks elapsed);
std::optional<projectile_warning> observe_player_threat(warning_state &state, int32_t distance, bool targeted, bool inhibited, math::random_state &random);

std::optional<projectile_warning> finish_warning_step(warning_state &state);

} // namespace tfx::weapons
