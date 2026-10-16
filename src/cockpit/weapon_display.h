#pragma once

#include <optional>
#include "cockpit/attitude_display.h"
#include "cockpit/hud_text.h"
#include "flight/aircraft.h"

namespace tfx::cockpit {

enum class aiming_mode { navigation, air, ground };
struct weapon_display_state {
  aiming_mode mode{aiming_mode::navigation};
  flight::player_aircraft aircraft{flight::player_aircraft::eurofighter};
  std::string_view weapon;
  int32_t range{0};
  std::optional<vec2<int16_t>> bomb_impact{};
  bool cannon{true};
  int16_t ammunition{0};
  bool suppressed{false};
  bool air_lock{false};
  bool ground_lock{false};
  bool contact_visible{false};
  bool limited{true};
  attitude_display_state attitude;
  hud_text_state flight;
  std::array<vec2<int16_t>,5> cannon_path{};
};

// Native navigation/air/ground HUD painters. Target-acquisition and navigation
// controllers supply their cues separately from the weapon layout itself.
class weapon_display {
private:
  instrument_assets const &assets;
  attitude_display attitude;
  hud_text numbers;
  resources::indexed_image framing;

public:
  weapon_display(instrument_assets const &assets, resources::archive const &game);
  void draw_forward(render::software_renderer &renderer, weapon_display_state const &state, render::framebuffer *coverage = nullptr) const;
  void draw(render::software_renderer &renderer, weapon_display_state const &state, render::framebuffer *coverage = nullptr, vec2<int> const &line_limit = {319,199}) const;
};

} // namespace tfx::cockpit
