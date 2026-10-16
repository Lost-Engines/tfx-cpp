#pragma once

#include "weapons/projectile.h"

namespace tfx::weapons {

uint8_t constexpr bomb_impact_category{9};

// Native 0xa29dc predicts category-9 bomb impact without creating a live shot.
vec3<int32_t> predict_bomb_impact(definition const &weapon, uint8_t index, vec3<int32_t> const &anchor_q8,
  vec3<math::angle> const &angles, int32_t speed, vec2<int32_t> const &height_bounds);

} // namespace tfx::weapons
