#include "model_point.h"
#include <limits>

namespace tfx::render {

bool model_point(framebuffer &output, vec3<int32_t> const &camera_origin, camera const &view, unsigned int const pixel_size, uint8_t const colour) {
  int32_t const depth{camera_origin.z >> 16};
  int16_t constexpr near_depth{16};
  if(depth <= near_depth) return true;
  // These distant-point handlers retain SAR 8 even in the missile-nose view.
  unsigned int constexpr shift{8};
  vec2<int32_t> const quotient{(camera_origin.x >> shift) / depth,(camera_origin.y >> shift) / depth};
  if(quotient.x < std::numeric_limits<int16_t>::min() || quotient.x > std::numeric_limits<int16_t>::max() || quotient.y < std::numeric_limits<int16_t>::min() || quotient.y > std::numeric_limits<int16_t>::max()) return false;
  vec2<int16_t> const point{
    math::signed_word(static_cast<uint16_t>(quotient.x + static_cast<int32_t>(view.projection_origin.x))),
    math::signed_word(static_cast<uint16_t>(quotient.y + static_cast<int32_t>(view.projection_origin.y))),
  };
  if(point.x < view.viewport_minimum.x || point.x > view.viewport_maximum.x || point.y < view.viewport_minimum.y || point.y > view.viewport_maximum.y) return true;
  for(unsigned int y{0}; y != pixel_size; ++y) for(unsigned int x{0}; x != pixel_size; ++x) {
    // The native two-pixel callback clips its anchor only. A right-edge second
    // pixel can therefore wrap to the following VGA row; retain linear writes.
    int const offset{(point.y + static_cast<int>(y)) * screen_width + point.x + static_cast<int>(x)};
    if(offset >= 0 && offset < static_cast<int>(output.pixels.size())) output.pixels[static_cast<unsigned int>(offset)] = colour;
  }
  return true;
}

} // namespace tfx::render
