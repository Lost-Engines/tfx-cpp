#include "camera.h"
#include <cmath>

namespace tfx::render {

vec3d camera::transform(vec3d const &world) const {
  auto const relative{world - position};
  return {relative.dot(right), relative.dot(down), relative.dot(forward)};
}
vec2d camera::project(vec3d const &point) const {
  return {projection_origin.x + point.x * focal_length / point.z,projection_origin.y + point.y * focal_length / point.z};
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
  // Native 0xdabd8 constructs the view matrix separately from the component matrix.
  // Its ordered shifts differ by a unit in some entries; negating an Euler matrix loses that distinction.
  auto const &table{math::sine_table()};
  auto const sine{[&](int const phase) { return static_cast<int32_t>(table[static_cast<unsigned int>(phase) & (math::angle_steps - 1)]); }};
  auto const cosine{[&](int const phase) { return sine(phase + math::angle_steps / 4); }};
  int const pitch{angles.x >> 6}, yaw{angles.y >> 6}, roll{angles.z >> 6};
  auto const sp{sine(pitch)}, s{sine(yaw + roll)}, t{sine(yaw - roll)}, c{cosine(yaw + roll)}, d{cosine(yaw - roll)};
  auto const multiply{[](int32_t const a, int32_t const b) { return (a * b) >> math::matrix_fraction_bits; }};
  mat3<int32_t> matrix;
  matrix.data = {
    (-multiply(d - c,sp) + c + d) >> 1,
    (sine(pitch + roll) - sine(pitch - roll)) >> 1,
    (multiply(s - t,sp) + s + t) >> 1,
    -((multiply(s + t,sp) + s - t) >> 1),
    (cosine(pitch + roll) + cosine(pitch - roll)) >> 1,
    (multiply(c + d,sp) + c - d) >> 1,
    -((sine(pitch + yaw) - sine(pitch - yaw)) >> 1),
    -sp,
    (cosine(pitch - yaw) + cosine(pitch + yaw)) >> 1,
  };
  for(auto &value : matrix.data) value = math::signed_word(static_cast<uint16_t>(value));
  // Native 0xb9b7a orbits in signed Q16 coordinates. XOR with the phase mask
  // selects -angle minus one table step, including that original offset at zero.
  auto const product{[](int32_t const a, int32_t const b) { return std::bit_cast<int32_t>(static_cast<uint32_t>(a) * static_cast<uint32_t>(b)); }};
  int const reverse_pitch{static_cast<int>(math::angle_steps - 1) - pitch}, reverse_yaw{static_cast<int>(math::angle_steps - 1) - yaw};
  int32_t const horizontal{product(cosine(reverse_pitch),distance) >> math::matrix_fraction_bits};
  auto const doubled{[&](int32_t const a, int32_t const b) { return std::bit_cast<int32_t>(0u - static_cast<uint32_t>(product(a,b)) * 2u); }};
  vec3<int32_t> const position{doubled(sine(reverse_yaw),horizontal),doubled(sine(reverse_pitch),distance),doubled(cosine(reverse_yaw),horizontal)};
  return {
    .position{vec3d{position} / 65536},
    .right{vec3d{vec3<int32_t>{matrix.data[0],matrix.data[3],matrix.data[6]}} / math::matrix_unit},
    .down{vec3d{vec3<int32_t>{matrix.data[1],matrix.data[4],matrix.data[7]}} / math::matrix_unit},
    .forward{vec3d{vec3<int32_t>{matrix.data[2],matrix.data[5],matrix.data[8]}} / math::matrix_unit},
    .projection_origin{vec2d{projection_origin}},
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
