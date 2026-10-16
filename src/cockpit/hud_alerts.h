#pragma once

#include "cockpit/instrument_assets.h"
#include "render/software_renderer.h"
#include "simulation/timing.h"

namespace tfx::cockpit {

struct hud_alert_state {
  hud_alert alert{hud_alert::bingo};
  int16_t remaining{0};
};
class hud_alerts {
private:
  instrument_assets const &assets;
  hud_alert_state state;

public:
  explicit hud_alerts(instrument_assets const &assets, hud_alert_state initial = {});
  hud_alert_state const &value() const;
  void show(hud_alert alert);
  void check_fuel(double fuel);
  void draw(render::software_renderer &renderer, vec2<int16_t> const &offset, simulation::timer_ticks elapsed, render::framebuffer *coverage = nullptr);
};

} // namespace tfx::cockpit
