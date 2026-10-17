#pragma once

#include "definition.h"

namespace tfx::world {

// SSD constructors add component metadata to the actor angles in WORDs;
// an unrotated binding ignores the metadata triple entirely.
inline vec3<math::angle> model_orientation(vec3<math::angle> const &actor, model_part const &part, math::angle const tile_heading = 0, part_orientation const orientation = part_orientation::terrain_axes) {
  auto result{part.rotation_mode ? actor + part.rotation : vec3<math::angle>{actor}};
  if(orientation == part_orientation::terrain_axes) result.y = static_cast<math::angle>(result.y + tile_heading);
  return result;
}

} // namespace tfx::world
