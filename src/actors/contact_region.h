#pragma once

#include "math/native.h"

namespace tfx::actors {

struct contact_region {
  vec3<int32_t> centre;
  vec3<int32_t> extent;
  bool contains(vec3<int32_t> const &position) const;
};
contact_region nearby_surface_region(vec3<int32_t> const &previous, vec3<int32_t> const &current);

} // namespace tfx::actors
