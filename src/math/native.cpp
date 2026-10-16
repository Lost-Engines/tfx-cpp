#include "native.h"
#include <cmath>
#include <numbers>
#include <algorithm>
#include "math/attitude.h"

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

vec2<angle> bearing(vec3<int32_t> const &from, vec3<int32_t> const &to) {
  // Native 0xc9714: wrapped coordinate differences, Chebyshev pitch distance, then signed-word angle inputs.
  auto const delta{[](int32_t const a, int32_t const b) { return std::bit_cast<int32_t>(static_cast<uint32_t>(a) - static_cast<uint32_t>(b)); }};
  auto const magnitude{[&](int32_t const value) { return value < 0 ? delta(0,value) : value; }};
  auto const angle_to{[](int32_t y, int32_t x) {
    while(y < -32768 || y > 32767 || x < -32768 || x > 32767) { y >>= 1; x >>= 1; }
    return direction_angle(static_cast<int16_t>(y),static_cast<int16_t>(x));
  }};
  int32_t const x{delta(to.x,from.x)}, y{delta(to.y,from.y)}, z{delta(to.z,from.z)};
  return {angle_to(y,std::max(magnitude(x),magnitude(z))),angle_to(x,z)};
}

int16_t distance_word(vec3<int16_t> const &offset) {
  /// Native 0xcbe94 / 0xd14b4: floor of the unsigned squared magnitude, returned in a signed word.
  auto const square{[](int32_t const value) { return static_cast<uint32_t>(value * value); }};
  auto const squared{square(offset.x) + square(offset.y) + square(offset.z)};
  return signed_word(static_cast<uint16_t>(std::sqrt(static_cast<double>(squared))));
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

vec3<int32_t> place_anchor(vec3<int32_t> const &origin, vec3<angle> const &angles, vec3<int16_t> const &anchor) {
  // Native 0xb81de adds each signed high-word product separately. One dot product followed by a shift loses its rounding rules.
  auto result{vec3<int32_t>{origin}};
  auto const matrix{rotation_words(angles)};
  for(unsigned int row{0}; row != 3; ++row) for(unsigned int column{0}; column != 3; ++column) {
    int32_t const term{(static_cast<int32_t>(anchor[column]) * matrix.data[column * 3 + row]) >> 16};
    result[row] = std::bit_cast<int32_t>(static_cast<uint32_t>(result[row]) + static_cast<uint32_t>(term));
  }
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

int16_t jitter_state::perturb(int16_t const coordinate, unsigned int const shift) {
  /// Native vertex jitter's distinct ADD/ADC ordering at 0xbc13a, followed by word SHL/SAR
  auto const sum{static_cast<unsigned int>(x) + y};
  x = static_cast<uint16_t>(sum);
  y = static_cast<uint16_t>(y + x + (sum > 65535));
  auto const count{shift & 31};
  int const delta{signed_word(static_cast<uint16_t>(static_cast<unsigned int>(x) << count)) >> count};
  return signed_word(static_cast<uint16_t>(coordinate + delta));
}

} // namespace tfx::math
