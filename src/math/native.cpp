#include "native.h"
#include <cmath>
#include <numbers>

namespace tfx::math {

std::array<int16_t, angle_steps> const &sine_table() {
  /// Reconstruct the original integer sine samples mathematically, including the negative-peak quirk
  static auto const table{[]{
    std::array<int16_t, angle_steps> result;
    for(unsigned int i{0}; i != angle_steps; ++i) result[i] = static_cast<int16_t>(std::sin(i * 2 * std::numbers::pi / angle_steps) * 32767);
    result[angle_steps * 3 / 4] = -32766;                                         // native table differs from trunc(sin * 32767) at this one entry
    return result;
  }()};
  return table;
}

mat3<int32_t> rotation_words(vec3<angle> const &angles) {
  /// Native component generator, 2.05 file 0xdad88; stored words are column-major
  auto const &table{sine_table()};
  auto const sine{[&table](int const phase){ return static_cast<int32_t>(table[static_cast<unsigned int>(phase) & (angle_steps - 1)]); }};
  auto const cosine{[&sine](int const phase){ return sine(phase + angle_steps / 4); }};
  auto const multiply{[](int32_t const a, int32_t const b){ return (a * b) >> matrix_fraction_bits; }};
  int const pitch{angles.x >> 6}, yaw{angles.y >> 6}, roll{angles.z >> 6};
  auto const sp{sine(pitch)}, s{sine(yaw + roll)}, t{sine(yaw - roll)}, c{cosine(yaw + roll)}, d{cosine(yaw - roll)};
  mat3<int32_t> result;
  result.data = {
    (multiply(d - c, sp) + c + d) >> 1,
    -(sine(pitch + roll) - sine(pitch - roll)) >> 1,
    (multiply(s - t, sp) - s - t) >> 1,
    (-multiply(s + t, sp) + s - t) >> 1,
    (cosine(pitch + roll) + cosine(pitch - roll)) >> 1,
    -((multiply(c + d, sp) + d - c) >> 1),
    (sine(pitch + yaw) - sine(pitch - yaw)) >> 1,
    sp,
    (cosine(pitch - yaw) + cosine(pitch + yaw)) >> 1,
  };
  for(auto &value : result.data) value = signed_word(static_cast<uint16_t>(value));
  return result;
}

mat3d rotation(vec3<angle> const &angles) {
  return mat3d{rotation_words(angles)} / static_cast<double>(matrix_unit);
}

vec3d rotate_tile(vec3d const &position, angle const heading) {
  /// The terrain loader selects exact quarter-turn callbacks, not the component sine matrix
  switch(heading >> 14) {
  case 1: return {position.z, position.y, -position.x};
  case 2: return {-position.x, position.y, -position.z};
  case 3: return {-position.z, position.y, position.x};
  default: return vec3d{position};
  }
}

uint16_t random_state::next() {
  /// Original ADD/ADC generator at 2.05 file 0xc98a3, returning the updated high word
  auto const sum{static_cast<unsigned int>(high) + low};
  high = static_cast<uint16_t>(sum);
  low = static_cast<uint16_t>(low + high + (sum > 65535));
  return high;
}

} // namespace tfx::math
