#include "model_transform.h"
#include <cmath>

namespace tfx::render {

vec3<int32_t> scale_model_cache(vec3<int32_t> const &origin, uint8_t const scale) {
  if(scale == 0 || scale == 1 || scale == 255) return vec3<int32_t>{origin};
  auto const factor{std::bit_cast<int8_t>(scale)};
  vec3<int32_t> result;
  for(unsigned int axis{0}; axis != 3; ++axis) {
    if(factor > 0) result[axis] = origin[axis] / factor;
    else {
      auto const multiplier{std::bit_cast<int8_t>(static_cast<uint8_t>(0u - scale))};
      result[axis] = std::bit_cast<int32_t>(static_cast<uint32_t>(origin[axis]) * static_cast<uint32_t>(multiplier));
    }
  }
  return result;
}

model_transform::model_transform(mat3<int32_t> const &view, vec3<math::angle> const &angles, vec3<int32_t> const &origin) : basis{view}, camera_origin{origin} {
  // BABCB bypasses the component generator when every angle is zero. Applying
  // an identity sine matrix would incorrectly reduce its diagonal by one.
  if(!angles.x && !angles.y && !angles.z) return;
  auto const body{math::rotation_words(angles)};
  for(unsigned int row{0}; row != 3; ++row) for(unsigned int column{0}; column != 3; ++column) {
    uint32_t sum{0};
    for(unsigned int axis{0}; axis != 3; ++axis) sum += static_cast<uint32_t>(view.data[row * 3 + axis]) * static_cast<uint32_t>(body.data[column * 3 + axis]);
    // B972A wraps each dword dot product before storing its signed Q15 word.
    basis.data[row * 3 + column] = math::signed_word(static_cast<uint16_t>(std::bit_cast<int32_t>(sum) >> math::matrix_fraction_bits));
  }
}
mat3<int32_t> const &model_transform::matrix() const { return basis; }
vec3d model_transform::point(vec3d const &position, double const projection_scale) const {
  double const multiplier{2 / projection_scale};
  auto const raw{position * multiplier};
  vec3<int32_t> result;
  for(unsigned int row{0}; row != 3; ++row) {
    double value{camera_origin[row] * multiplier};
    for(unsigned int axis{0}; axis != 3; ++axis) value += basis.data[row * 3 + axis] * raw[axis];
    result[row] = std::bit_cast<int32_t>(static_cast<uint32_t>(static_cast<int64_t>(std::nearbyint(value))));
  }
  return vec3d{result} * (projection_scale / 65536);
}

} // namespace tfx::render
