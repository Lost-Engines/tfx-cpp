#pragma once

#include "models/shape.h"
#include "render/camera.h"

namespace tfx::render {

// Original BC660 rounded quad: reject near vertices, project camera-space
// edge midpoints, then paint the centre and four DAF50 corner fans.
bool rounded_model_polygon(framebuffer &output, std::span<models::model_vertex const> vertices, camera const &view, uint8_t colour, int mode, uint16_t &procedural_seed);

} // namespace tfx::render
