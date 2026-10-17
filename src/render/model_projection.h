#pragma once

#include "models/shape.h"
#include "render/camera.h"

namespace tfx::render {

// Recover the original signed camera dwords after model-unit normalization.
std::optional<vec3<int32_t>> model_camera_point(models::model_vertex const &vertex);
// B9434 ordinary projection; a missing result includes the original word-IDIV
// overflow domain, which has no completed native frame.
std::optional<vec2<int16_t>> project_model_point(vec3<int32_t> const &point, camera const &view);

} // namespace tfx::render
