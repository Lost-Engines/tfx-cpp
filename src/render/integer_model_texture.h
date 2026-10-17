#pragma once

#include "models/shape.h"
#include "render/camera.h"
#include "render/colour_remap.h"

namespace tfx::render {

// Original model texture dispatch, including unsigned UV near clipping.
// Returns false for undefined native projection inputs.
bool integer_model_texture(framebuffer &output, std::span<models::model_vertex const> vertices, camera const &view, std::span<uint8_t const> texture, colour_map const &remap);

} // namespace tfx::render
