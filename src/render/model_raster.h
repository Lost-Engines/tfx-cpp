#pragma once

#include "model_polygon.h"

namespace tfx::render {

// Authored native primitives share one dispatch in live worlds and frame
// comparisons. False leaves inspection/unsupported drawing to the host.
bool paint_model_primitive(framebuffer &output, models::primitive const &source, std::span<models::model_vertex const> vertices, camera const &view, std::span<uint8_t const> texture, colour_map const *remap, uint16_t &procedural_seed);

} // namespace tfx::render
