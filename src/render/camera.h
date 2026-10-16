#pragma once

#include "math/native.h"
#include "math/attitude.h"
#include "render/framebuffer.h"

namespace tfx::render {

enum class projection_mode { continuous, original_model };

struct camera {
  vec3d position;
  vec3d right;
  vec3d down;
  vec3d forward;
  vec2d projection_origin{centre_x,centre_y};
  double focal_distance{focal_length};
  projection_mode projection{projection_mode::continuous};
  double near_distance{16};
  double far_distance{20000};
  vec3d transform(vec3d const &world) const;
  vec2d project(vec3d const &camera_position, double projection_scale = 1) const;
};

camera aircraft_camera(vec3f const &position, math::attitude const &orientation);

camera orbit_camera(vec3<math::angle> const &angles, int32_t distance, vec2d const &projection_origin);

camera original_camera(vec3<int32_t> const &position_q16, mat3<int32_t> const &matrix, vec2d const &projection_origin);

camera inspection_camera(vec3d const &position, double heading, double pitch);

} // namespace tfx::render
