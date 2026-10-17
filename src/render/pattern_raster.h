#pragma once

#include "integer_polygon.h"

namespace tfx::render {

void pattern_pixel(framebuffer &output, int x, int y, uint8_t colour, int mode);
void pattern_span(framebuffer &output, uint16_t &seed, int y, double left, double right, uint8_t colour, int mode, int bottom, bool inclusive, bool paint = true);
// Native painters consume the clipped edge table from bottom to top.
void pattern_polygon(framebuffer &output, uint16_t &seed, std::span<polygon_span const> spans, uint8_t colour, int mode);

} // namespace tfx::render
