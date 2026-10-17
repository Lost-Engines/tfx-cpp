#pragma once

#include "render/framebuffer.h"

namespace tfx::render {

// Original solid 2D convex polygon path: signed-word clipping and Q16 edges.
void integer_polygon(framebuffer &output, std::span<vec2<int16_t> const> vertices, uint8_t colour, vec2<int16_t> const &minimum, vec2<int16_t> const &maximum);

} // namespace tfx::render
