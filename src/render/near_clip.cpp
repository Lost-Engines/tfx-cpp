#include "near_clip.h"

namespace tfx::render {
namespace {
int16_t word(int32_t const value) { return math::signed_word(static_cast<uint16_t>(value)); }
int32_t midpoint(int32_t const a, int32_t const b) { return std::bit_cast<int32_t>(static_cast<uint32_t>(a) + static_cast<uint32_t>(b)) >> 1; }
}

vec2<int32_t> intersect_near_plane(vec3<int32_t> const &outside, vec3<int32_t> const &inside) {
  int16_t lower{word(outside.z >> 16)}, upper{word(inside.z >> 16)};
  if(lower == model_near_depth) return {outside.x,outside.y};
  uint16_t path{0};
  // Original unrolled search bisects signed WORD depths, including overflow
  // before SAR. It records branch decisions low bit first. Equality adds a
  // sentinel next bit; the sixteenth comparison has no room for that sentinel.
  unsigned int constexpr depth_bits{16};
  for(unsigned int step{0}; step != depth_bits; ++step) {
    int16_t const centre{static_cast<int16_t>(word(lower + upper) >> 1)};
    if(centre == model_near_depth) {
      if(step != depth_bits - 1) path = static_cast<uint16_t>(path | (3u << step));
      break;
    }
    if(centre > model_near_depth) { upper = centre;path = static_cast<uint16_t>(path | (1u << step)); }
    else lower = centre;
  }
  vec2<int32_t> a{outside.x,outside.y}, b{inside.x,inside.y};
  bool upper_half{(path & 1) != 0};path >>= 1;
  for(;;) {
    auto &endpoint{upper_half ? b : a};
    endpoint = {midpoint(a.x,b.x),midpoint(a.y,b.y)};
    upper_half = (path & 1) != 0;path >>= 1;
    // The last set bit terminates replay; it is not another midpoint step.
    // The native loop still performs one midpoint when its path word is zero.
    if(!path) return vec2<int32_t>{endpoint};
  }
}

vec2<int16_t> project_near_plane(vec2<int32_t> const &point, aperture const opening, vec2<int16_t> const &origin) {
  unsigned int const shift{projection_shift(opening)};
  int32_t constexpr normal_coordinate_limit{2030}, screen_saturation{32000};
  int32_t const limit{normal_coordinate_limit * static_cast<int32_t>(1u << (shift - 8)) * 65536};
  auto const coordinate{[&](int32_t const value, int16_t const offset) {
    // Saturation writes a final screen word, without adding the origin. The
    // ordinary path retains arithmetic-shift rounding even for negative XY.
    if(value > limit) return static_cast<int16_t>(screen_saturation);
    if(value < -limit) return static_cast<int16_t>(-screen_saturation);
    return word((value >> (shift + 4)) + offset);
  }};
  return {coordinate(point.x,origin.x),coordinate(point.y,origin.y)};
}

} // namespace tfx::render
