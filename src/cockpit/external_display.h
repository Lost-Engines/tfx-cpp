#pragma once

#include "cockpit/instrument_assets.h"
#include "presentation/fonts.h"
#include "render/software_renderer.h"

namespace tfx::cockpit {

struct external_view_state {
  float height{0};
  int32_t speed{0};
  math::angle heading{0};
  bool enabled{true};
};
class external_display {
private:
  instrument_assets const &assets;
  presentation::fonts const &fonts;

public:
  external_display(instrument_assets const &assets, presentation::fonts const &fonts);
  void draw(render::software_renderer &renderer, external_view_state const &state, render::framebuffer *coverage = nullptr) const;
};

} // namespace tfx::cockpit
