#pragma once

#include "models/shape.h"
#include "render/camera.h"

namespace tfx::render {

// Project a flat model face through native Q16 projection and integer screen
// clipping. Returns false for inspection cameras or faces requiring the still
// separate near/far 3D clipping path; no pixels are changed in that case.
bool integer_model_polygon(framebuffer &output, std::span<models::model_vertex const> vertices, camera const &view, uint8_t colour);

} // namespace tfx::render
