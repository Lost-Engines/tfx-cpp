#pragma once

#include "models/shape.h"
#include "render/camera.h"
#include "render/colour_remap.h"

namespace tfx::render {

// Shared native polygon dispatch, used by live worlds and supplied-model
// frame comparisons. False leaves continuous/unsupported drawing to the host.
bool paint_model_polygon(framebuffer &output, models::primitive const &source, std::span<models::model_vertex const> vertices, camera const &view, std::span<uint8_t const> texture, colour_map const *remap, uint16_t &procedural_seed);

} // namespace tfx::render
