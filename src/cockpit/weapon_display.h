#pragma once

#include <optional>
#include "cockpit/attitude_display.h"
#include "cockpit/hud_text.h"
#include "cockpit/hud_alerts.h"
#include "cockpit/target_display.h"
#include "flight/aircraft.h"
#include "flight/landing.h"

namespace tfx::cockpit {

enum class aiming_mode { navigation, air, ground };
struct air_target_cue {
  air_target_reading reading;
  math::attitude orientation;
  vec2<int16_t> projected{0,0};
  vec2<int32_t> tracking_q8{0,0};
  bool acquiring{false};
};
struct target_animation {
  uint8_t blink{0};
  bool had_lock{false};
  target_sight sight{target_sight::normal};
};
struct weapon_effects {
  bool lock_acquired{false};
};
struct weapon_display_state {
  aiming_mode mode{aiming_mode::navigation};
  flight::player_aircraft aircraft{flight::player_aircraft::eurofighter};
  std::string_view weapon;
  int32_t range{0};
  uint8_t category{0};
  std::optional<vec2<int16_t>> bomb_impact{};
  std::optional<vec2<int16_t>> ground_marker{};
  std::optional<air_target_cue> air_target{};
  std::optional<air_target_cue> navigation_target{};
  std::optional<flight::landing_cue> landing{};
  bool cannon{true};
  int16_t ammunition{0};
  bool suppressed{false};
  bool air_lock{false};
  bool ground_lock{false};
  bool limited{true};
  simulation::timer_ticks elapsed{0};
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
  target_display targets;
  hud_alerts alerts;
  target_animation tracking;
  resources::indexed_image framing;

public:
  weapon_display(instrument_assets const &assets, resources::archive const &game);
  void reset_tracking();
  target_animation animation() const;
  void check_fuel(double fuel);
  void show_alert(hud_alert alert);
  hud_alert_state alert_state() const;
  weapon_effects draw_forward(render::software_renderer &renderer, weapon_display_state const &state, render::framebuffer *coverage = nullptr);
  void draw(render::software_renderer &renderer, weapon_display_state const &state, render::framebuffer *coverage = nullptr, vec2<int> const &line_limit = {319,199}) const;
};

} // namespace tfx::cockpit
