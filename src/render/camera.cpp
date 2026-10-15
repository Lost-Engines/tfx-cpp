#include "camera.h"
#include <cmath>

namespace tfx::render {

vec3d camera::transform(vec3d const &world) const {
  auto const relative{world - position};
  return {relative.dot(right), relative.dot(down), relative.dot(forward)};
}
vec2d camera::project(vec3d const &point) const {
  return {centre_x + point.x * focal_length / point.z, centre_y + point.y * focal_length / point.z};
}

camera aircraft_camera(vec3f const &position, math::attitude const &orientation) {
  double constexpr q15_unit{32767};
  return {
    .position{vec3d{position}},
    .right{vec3d{orientation.right} / q15_unit},
    .down{vec3d{orientation.down} / q15_unit},
    .forward{vec3d{orientation.forward} / q15_unit},
  };
}

camera inspection_camera(vec3d const &position, double const heading, double const pitch) {
  /// A free research camera, deliberately separate from the player's fixed-point pose handoff
  double const sh{std::sin(heading)}, ch{std::cos(heading)}, sp{std::sin(pitch)}, cp{std::cos(pitch)};
  return {
    .position{vec3d{position}},
    .right{ch,0,-sh},
    .down{sh * sp,cp,ch * sp},
    .forward{sh * cp,-sp,ch * cp},
  };
}

} // namespace tfx::render
