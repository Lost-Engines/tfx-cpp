#pragma once

#include "math/native.h"
#include "render/aperture.h"

namespace tfx::render {

int16_t constexpr model_near_depth{16};
// Native 0xd7d22: outside depth <=16, inside depth >16, using the signed high
// words of the supplied Q16 camera positions. XY remains Q16 on return.
vec2<int32_t> intersect_near_plane(vec3<int32_t> const &outside, vec3<int32_t> const &inside);
// Native 0xd7c90: near-plane projection uses shifts and saturation, distinct
// from the ordinary vertex loop's signed division.
vec2<int16_t> project_near_plane(vec2<int32_t> const &point, aperture opening, vec2<int16_t> const &origin);

} // namespace tfx::render
