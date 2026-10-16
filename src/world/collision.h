#pragma once

#include <cstdint>
#include "math/native.h"

namespace tfx::world {

struct collision_box {
  vec3<int16_t> minimum;
  vec3<int16_t> maximum;
};
struct collision_segment {
  vec3<int16_t> previous;
  vec3<int16_t> current;
};

bool intersects(collision_box const &box, collision_segment const &movement, bool diagonal = false);

} // namespace tfx::world
