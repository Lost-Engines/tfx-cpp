#pragma once

#include "render/clipping.h"
#include "resources/media.h"

namespace tfx::render {

void draw_sprite(framebuffer &target, resources::indexed_image const &image, vec2<int> const &centre, framebuffer *coverage = nullptr, raster_clip const &clip = {});
void draw_monochrome(framebuffer &target, resources::monochrome_image const &image, vec2<int> const &position, uint8_t colour, framebuffer *coverage = nullptr, raster_clip const &clip = {});

} // namespace tfx::render
