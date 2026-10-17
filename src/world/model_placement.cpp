#include "model_placement.h"
#include "instance.h"

namespace tfx::world {

model_placement place_model_part(render::point_projection const &view, vec3<int32_t> const &assembly_q16, vec3<int16_t> const &anchor, math::angle const heading, part_position const placement, int16_t const radius) {
  vec3<int16_t> const origin{
    math::signed_word(static_cast<uint16_t>(assembly_q16.x >> 16)),
    math::signed_word(static_cast<uint16_t>(assembly_q16.y >> 16)),
    math::signed_word(static_cast<uint16_t>(assembly_q16.z >> 16)),
  };
  if(placement == part_position::assembly_origin) return {
    .position{vec3<int16_t>{origin}},
    .camera_origin{view.camera_fixed(assembly_q16)},
    .visible{true}, // Whole-assembly admission belongs to the caller.
  };
  auto const point{place_instance_point(anchor,origin,heading)};
  auto const camera{placement == part_position::fixed_anchor ? view.camera_fixed(vec3<int32_t>{vec3<uint32_t>{point} * 65536u}) : view.camera_integer(vec3<int32_t>{point})};
  return {
    .position{vec3<int16_t>{point}},
    .camera_origin{vec3<int32_t>{camera}},
    .visible{view.camera_sphere_visible(camera,radius)},
  };
}

} // namespace tfx::world
