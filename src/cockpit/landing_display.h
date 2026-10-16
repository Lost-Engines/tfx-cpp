#pragma once

#include "cockpit/instrument_assets.h"
#include "flight/landing.h"
#include "render/software_renderer.h"

namespace tfx::cockpit {

void draw_landing_cue(render::software_renderer &renderer, instrument_assets const &assets,
  flight::landing_cue const &cue, vec2<int16_t> const &offset, render::framebuffer *coverage = nullptr);

} // namespace tfx::cockpit
