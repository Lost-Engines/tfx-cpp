#pragma once

#include "models/shape.h"
#include "render/camera.h"

namespace tfx::render {

// Original BC660 rounded quads and BCA58 standalone arcs. Both omit near
// corners; quads project camera-space midpoints before their corner fans.
bool rounded_model_polygon(framebuffer &output, std::span<models::model_vertex const> vertices, camera const &view, uint8_t colour, int mode, uint16_t &procedural_seed);

} // namespace tfx::render
