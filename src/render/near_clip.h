#pragma once

#include "math/native.h"
#include "render/aperture.h"

namespace tfx::render {

int16_t constexpr model_near_depth{16};
struct shaded_near_vertex {
  vec2<int32_t> position;
  uint16_t shade_q8;
};
// Native 0xd824e uses the same depth path, also averaging the 8.8 colour
// attribute in unsigned dwords while XY keeps signed wrapped midpoints.
shaded_near_vertex intersect_shaded_near_plane(vec3<int32_t> const &outside, vec3<int32_t> const &inside, uint16_t outside_shade, uint16_t inside_shade);

struct textured_near_vertex {
  vec2<int32_t> position;
  vec2<uint16_t> uv_q7;
};
// D87E0 replays the same depth decisions for two unsigned UV words.
textured_near_vertex intersect_textured_near_plane(vec3<int32_t> const &outside, vec3<int32_t> const &inside, vec2<uint16_t> const &outside_uv, vec2<uint16_t> const &inside_uv);

// Native 0xd7d22: outside depth <=16, inside depth >16, using the signed high
// words of the supplied Q16 camera positions. XY remains Q16 on return.
vec2<int32_t> intersect_near_plane(vec3<int32_t> const &outside, vec3<int32_t> const &inside);
// Native 0xd7c90: near-plane projection uses shifts and saturation, distinct
// from the ordinary vertex loop's signed division.
vec2<int16_t> project_near_plane(vec2<int32_t> const &point, aperture opening, vec2<int16_t> const &origin);

} // namespace tfx::render
