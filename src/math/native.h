#pragma once

#include <array>
#include <bit>
#include <cstdint>
#include "vectorstorm/vector/vector2.h"
#include "vectorstorm/vector/vector3.h"
#include "vectorstorm/matrix/matrix3.h"

namespace tfx::math {

using angle = uint16_t;
unsigned int constexpr angle_steps{1024};
int constexpr matrix_fraction_bits{15};
int constexpr matrix_unit{1 << matrix_fraction_bits};

constexpr int16_t signed_word(uint16_t const value) {
  return std::bit_cast<int16_t>(value);
}
std::array<int16_t, angle_steps> const &sine_table();
int16_t distance_word(vec3<int16_t> const &offset);
mat3<int32_t> rotation_words(vec3<angle> const &angles);
mat3d rotation(vec3<angle> const &angles);
vec3d rotate_tile(vec3d const &position, angle heading);

struct random_state {
  uint16_t low{0x5926};
  uint16_t high{0x3141};
  uint16_t next();
};

struct jitter_state {
  uint16_t x{0x3141};
  uint16_t y{0x5926};
  int16_t perturb(int16_t coordinate, unsigned int shift);
};

} // namespace tfx::math
