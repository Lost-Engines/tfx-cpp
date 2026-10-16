#pragma once

#include "render/framebuffer.h"

namespace tfx::render {

struct raster_clip {
  // Initial inspection-driver limits. Native viewport calls replace both pairs below.
  vec2<int> glyph_minimum{0,0};
  vec2<int> glyph_limit{screen_width,screen_height};
  vec2<int> sprite_minimum{0,0};
  vec2<int> sprite_limit{screen_width - 1,screen_height};

  static raster_clip viewport(vec2<int> const &minimum, vec2<int> const &maximum) {
    // Native 0xc0634: glyph X ends at the supplied word; sprite X rounds in VGA groups.
    // Bottom Y becomes exclusive for both, while the glyph X word does not increment.
    return {
      .glyph_minimum{vec2<int>{minimum}},
      .glyph_limit{maximum.x,maximum.y + 1},
      .sprite_minimum{minimum.x & ~3,minimum.y},
      .sprite_limit{(maximum.x + 3) & ~3,maximum.y + 1},
    };
  }
};

} // namespace tfx::render
