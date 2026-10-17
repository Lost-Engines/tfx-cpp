#pragma once

#include <optional>
#include "definition.h"
#include "render/point_projection.h"

namespace tfx::world {

struct model_placement {
  vec3<int16_t> position;
  vec3<int32_t> camera_origin;
  bool visible;
};
// Native B635C reuses an admitted assembly's fixed cache. B6438 instead
// queries a word anchor after quarter-turn placement; B668C uses its fixed
// counterpart. Both remain independent of the
// model's full visual Euler rotation.
model_placement place_model_part(render::point_projection const &view, vec3<int32_t> const &assembly_q16, vec3<int16_t> const &anchor, math::angle heading, part_position placement, int16_t radius);

// B6A44 admits shadows only for object Y in (-1024, 0], retaining full X/Z
// fractions and the game's current ground-height word for the projected plane.
std::optional<model_placement> place_model_shadow(render::point_projection const &view, vec3<int32_t> const &assembly_q16, int16_t ground_height, int16_t radius);

} // namespace tfx::world
