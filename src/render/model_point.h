#pragma once

#include "camera.h"

namespace tfx::render {

// Native BB021/BB094 distant representations: clipped anchor, one/two pixels.
// False identifies an IDIV-overflow input, outside the original defined domain.
bool model_point(framebuffer &output, vec3<int32_t> const &camera_origin, camera const &view, unsigned int pixel_size, uint8_t colour);

} // namespace tfx::render
