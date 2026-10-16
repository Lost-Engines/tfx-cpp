#pragma once

#include <optional>
#include "math/native.h"

namespace tfx::render {

// Native HUD/world point projection is separate from the polygon vertex loop.
struct point_projection {
  mat3<int32_t> matrix;
  vec3<int32_t> position_q16;
  vec2<int16_t> origin;
  std::optional<vec2<int16_t>> integer(vec3<int32_t> const &point) const;
  std::optional<vec2<int16_t>> fixed(vec3<int32_t> const &point_q16) const;

private:
  std::optional<vec2<int16_t>> project(vec3<int32_t> const &camera_point) const;
};

} // namespace tfx::render
