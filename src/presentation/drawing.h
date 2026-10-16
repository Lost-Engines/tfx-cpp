#pragma once

#include "render/framebuffer.h"

namespace tfx::presentation {

bool clip_line(vec2<int> &from, vec2<int> &to, vec2<int> const &minimum, vec2<int> const &maximum);

// Inclusive pixel lines and the original nearest-endpoint integer clipping rule.
void draw_line(render::framebuffer &image, vec2<int> from, vec2<int> const &to, uint8_t colour);
void draw_clipped_line(render::framebuffer &image, vec2<int> from, vec2<int> to,
  vec2<int> const &minimum, vec2<int> const &maximum, uint8_t colour);

void draw_patterned_line(render::framebuffer &image, vec2<int> from, vec2<int> to,
  vec2<int> const &minimum, vec2<int> const &maximum, uint8_t colour, uint8_t pattern);

unsigned int draw_partial_line(render::framebuffer &image, vec2<int> from, vec2<int> to,
  vec2<int> const &minimum, vec2<int> const &maximum, uint8_t colour, unsigned int extent);

} // namespace tfx::presentation
