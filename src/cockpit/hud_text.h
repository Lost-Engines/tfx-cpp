#pragma once

#include "cockpit/instrument_assets.h"
#include "render/software_renderer.h"

namespace tfx::cockpit {

struct hud_text_state {
  float height{0};
  int32_t speed{0};
  double mach{0};
  float load{0};
  float throttle{0};
  vec3<int32_t> position{0,0,0};
  bool air_brake{false};
  bool brake_chute{false};
  bool arrester_cable{false};
  vec2<int16_t> offset{0,0};
};
class hud_text {
private:
  instrument_assets const &assets;

public:
  explicit hud_text(instrument_assets const &assets);
  void draw_values(render::software_renderer &renderer, hud_text_state const &state, render::framebuffer *coverage = nullptr) const;
  void draw_messages(render::software_renderer &renderer, hud_text_state const &state, render::framebuffer *coverage = nullptr) const;
  void draw(render::software_renderer &renderer, hud_text_state const &state, render::framebuffer *coverage = nullptr) const;
};

} // namespace tfx::cockpit
