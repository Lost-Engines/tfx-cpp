#pragma once

#include "resources/media.h"

namespace tfx::render {

void draw_sprite(framebuffer &target, resources::indexed_image const &image, vec2<int> const &centre, framebuffer *coverage = nullptr);
void draw_monochrome(framebuffer &target, resources::monochrome_image const &image, vec2<int> const &position, uint8_t colour, framebuffer *coverage = nullptr);

} // namespace tfx::render
