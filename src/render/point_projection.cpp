#include "point_projection.h"
#include <bit>

namespace tfx::render {
namespace {
int32_t wrap(uint32_t const value) { return std::bit_cast<int32_t>(value); }
}

std::optional<vec2<int16_t>> point_projection::project(vec3<int32_t> const &camera_point) const {
  // Native 0xc5759/0xc57d1 use a truncated reciprocal, then the signed high
  // product. Replacing this with direct division loses negative-pixel rounding.
  int constexpr minimum_depth{16}, maximum_depth{20000};
  int32_t const depth{camera_point.z >> 16};
  if(depth < minimum_depth || depth > maximum_depth) return std::nullopt;
  auto const reciprocal{static_cast<int32_t>((uint64_t{1} << 32) / static_cast<uint32_t>(depth))};
  auto const coordinate{[&](int32_t const value, int16_t const offset) {
    auto const high{(static_cast<int64_t>(value >> 8) * reciprocal) >> 32};
    return math::signed_word(static_cast<uint16_t>(high + offset));
  }};
  return vec2<int16_t>{coordinate(camera_point.x,origin.x),coordinate(camera_point.y,origin.y)};
}
std::optional<vec2<int16_t>> point_projection::integer(vec3<int32_t> const &point) const {
  // Native 0xb9c9c subtracts/stores words before extending them. Camera
  // fractional position and coordinate bits above bit 15 are deliberately lost.
  vec3<int16_t> delta;
  for(unsigned int axis{0}; axis != 3; ++axis) delta[axis] = math::signed_word(static_cast<uint16_t>(static_cast<uint32_t>(point[axis]) - (static_cast<uint32_t>(position_q16[axis]) >> 16)));
  vec3<int32_t> transformed;
  for(unsigned int row{0}; row != 3; ++row) {
    uint32_t sum{0};
    for(unsigned int axis{0}; axis != 3; ++axis) sum += static_cast<uint32_t>(delta[axis]) * static_cast<uint32_t>(matrix.data[row * 3 + axis]);
    transformed[row] = wrap(sum);
  }
  return project(transformed);
}
std::optional<vec2<int16_t>> point_projection::fixed(vec3<int32_t> const &point_q16) const {
  // Native 0xb9c84/0xb9d14 keep the full Q16 subtraction. Each matrix product
  // contributes its signed high dword separately before the wrapped row sum.
  vec3<int32_t> delta;
  for(unsigned int axis{0}; axis != 3; ++axis) delta[axis] = wrap(static_cast<uint32_t>(point_q16[axis]) - static_cast<uint32_t>(position_q16[axis]));
  vec3<int32_t> transformed;
  for(unsigned int row{0}; row != 3; ++row) {
    uint32_t sum{0};
    for(unsigned int axis{0}; axis != 3; ++axis) {
      int32_t const coefficient{wrap(static_cast<uint32_t>(static_cast<uint16_t>(matrix.data[row * 3 + axis])) << 16)};
      sum += static_cast<uint32_t>((static_cast<int64_t>(coefficient) * delta[axis]) >> 32);
    }
    transformed[row] = wrap(sum);
  }
  return project(transformed);
}

} // namespace tfx::render
