#pragma once

#include "math/native.h"
#include "math/attitude.h"
#include "render/framebuffer.h"

namespace tfx::render {

struct camera {
  vec3d position;
  vec3d right;
  vec3d down;
  vec3d forward;
  vec2d projection_origin{centre_x,centre_y};
  double near_distance{16};
  double far_distance{20000};
  vec3d transform(vec3d const &world) const;
  vec2d project(vec3d const &camera_position) const;
};

camera aircraft_camera(vec3f const &position, math::attitude const &orientation);

camera orbit_camera(vec3<math::angle> const &angles, int32_t distance, vec2d const &projection_origin);

camera inspection_camera(vec3d const &position, double heading, double pitch);

} // namespace tfx::render
