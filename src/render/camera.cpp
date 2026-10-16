#include "camera.h"
#include <cmath>

namespace tfx::render {

vec3d camera::transform(vec3d const &world) const {
  auto const relative{world - position};
  return {relative.dot(right), relative.dot(down), relative.dot(forward)};
}
vec2d camera::project(vec3d const &point) const {
  if(projection == projection_mode::original_model) {
    // Native 0xb9434: signed Q16 X/Y shifted by eight, divided by the signed
    // integer depth, then added to the viewport origin. IDIV truncates toward zero.
    double const depth{std::floor(point.z)};
    return projection_origin + vec2d{std::trunc(std::floor(point.x * 256) / depth),std::trunc(std::floor(point.y * 256) / depth)};
  }
  return {projection_origin.x + point.x * focal_distance / point.z,projection_origin.y + point.y * focal_distance / point.z};
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

camera orbit_camera(vec3<math::angle> const &angles, int32_t const distance, vec2d const &projection_origin) {
  auto const position{math::orbit_offset_q16({angles.x,angles.y},distance)};
  return original_camera(position,math::view_rotation_words(angles),projection_origin);
}

camera original_camera(vec3<int32_t> const &position_q16, mat3<int32_t> const &matrix, vec2d const &projection_origin) {
  return {
    .position{vec3d{position_q16} / 65536},
    .right{vec3d{vec3<int32_t>{matrix.data[0],matrix.data[1],matrix.data[2]}} / math::matrix_unit},
    .down{vec3d{vec3<int32_t>{matrix.data[3],matrix.data[4],matrix.data[5]}} / math::matrix_unit},
    .forward{vec3d{vec3<int32_t>{matrix.data[6],matrix.data[7],matrix.data[8]}} / math::matrix_unit},
    .projection_origin{vec2d{projection_origin}},
    .focal_distance{256},
    .projection{projection_mode::original_model},
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
