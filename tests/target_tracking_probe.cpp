#include <cstdlib>
#include <iostream>
#include <string_view>
#include <utility>
#include "cockpit/weapon_display.h"
#include "weapons/impact_prediction.h"

int main(int const argc, char const *const argv[]) try {
  bool const alerts_mode{argc == 3 && std::string_view{argv[2]} == "--alerts"};
  if(argc != 2 && !alerts_mode) throw std::runtime_error{"usage: target_tracking_probe DATA_DIRECTORY [--alerts]"};
  auto const archive{tfx::resources::find_game_archive(argv[1])};
  tfx::resources::archive const game{archive};
  tfx::resources::executable_tables const tables{archive.parent_path() / "TFX.DAT"};
  tfx::render::software_renderer renderer{tables};
  tfx::cockpit::weapon_display display{tables.instruments(),game};
  unsigned int reset{0},mode{0},aircraft{0},weapon{0},present{0},leader{0},ground{0};
  tfx::cockpit::weapon_display_state state;tfx::cockpit::air_target_cue cue;
  vec2<int16_t> ground_point{0,0};
  while(std::cin >> reset >> mode >> aircraft >> weapon >> state.limited >> state.suppressed >> state.air_lock >> state.ground_lock >> present >> cue.acquiring >> leader >> cue.projected.x >> cue.projected.y >> cue.tracking_q8.x >> cue.tracking_q8.y >> state.flight.position.x >> state.flight.position.y >> state.flight.position.z >> cue.reading.position_q8.x >> cue.reading.position_q8.y >> cue.reading.position_q8.z >> cue.reading.heading >> cue.reading.speed_q16) {
    for(auto *axis : {&cue.orientation.right,&cue.orientation.down,&cue.orientation.forward}) for(auto &coordinate : *axis) std::cin >> coordinate;
    std::cin >> ground >> ground_point.x >> ground_point.y >> state.attitude.offset.x >> state.attitude.offset.y;
    if(reset) display.reset_tracking();
    int request{-1};double fuel{10000};
    if(alerts_mode) std::cin >> request >> fuel >> state.elapsed;
    if(request >= 0) display.show_alert(static_cast<tfx::cockpit::hud_alert>(request));
    display.check_fuel(fuel);
    state.mode = static_cast<tfx::cockpit::aiming_mode>(mode);
    state.aircraft = static_cast<tfx::flight::player_aircraft>(aircraft + 1);
    state.weapon = tables.weapons.at(weapon).label;state.range = tables.weapons.at(weapon).range;state.category = tables.weapons.at(weapon).category;
    state.cannon = weapon == 0;state.ammunition = 1760;
    state.flight.offset = vec2<int16_t>{state.attitude.offset};
    state.attitude.projection_origin = {159,static_cast<int16_t>(56 + state.attitude.offset.y / 2)};
    state.cannon_path = {{{140,40},{145,45},{150,50},{155,55},{160,60}}};
    state.air_target.reset();cue.reading.name = "MiG-29 Fulcrum";
    if(present) state.air_target.emplace(cue);
    state.ground_marker.reset();if(ground) state.ground_marker.emplace(vec2<int16_t>{ground_point});
    state.bomb_impact.reset();if(state.category == tfx::weapons::bomb_impact_category) state.bomb_impact.emplace(160,60);
    renderer.output.pixels.fill(99);tfx::render::framebuffer coverage;
    auto const effects{display.draw_forward(renderer,state,&coverage)};
    auto const animation{display.animation()};
    std::array<int32_t,6> const header{animation.blink,animation.had_lock,animation.sight == tfx::cockpit::target_sight::compact,effects.lock_acquired,static_cast<int32_t>(std::to_underlying(display.alert_state().alert)),display.alert_state().remaining};
    std::cout.write(reinterpret_cast<char const*>(header.data()),(alerts_mode ? 6 : 4) * sizeof(int32_t));
    std::cout.write(reinterpret_cast<char const*>(renderer.output.pixels.data()),renderer.output.pixels.size());
    std::cout.write(reinterpret_cast<char const*>(coverage.pixels.data()),coverage.pixels.size());
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
