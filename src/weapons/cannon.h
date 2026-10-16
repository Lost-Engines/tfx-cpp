#pragma once

#include "flight/aircraft.h"
#include "weapons/runtime.h"

namespace tfx::weapons {

int16_t constexpr initial_cannon_ammunition{1760}, ammunition_per_release{10};
struct cannon_state {
  int16_t ammunition{initial_cannon_ammunition};
  uint16_t barrel{0};
};
struct cannon_context {
  flight::player_aircraft aircraft;
  vec3<int32_t> position;
  vec3<math::angle> angles;
  int32_t speed;
  bool trigger{false};
  bool gun_mode{true};
  bool fire_control{true};
  bool gun{true};
  bool inhibited{false};
  bool protected_player{false};
  bool crashed{false};
  bool ejected{false};
  bool landed{false};
};
std::optional<release> fire_cannon(cannon_state &state, cannon_context const &context, std::span<vec3<int16_t> const> mounts, math::random_state &random);

} // namespace tfx::weapons
