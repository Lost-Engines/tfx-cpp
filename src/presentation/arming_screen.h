#pragma once

#include "presentation/arming_preview.h"
#include "presentation/arming_widgets.h"
#include "resources/media.h"

namespace tfx::presentation {

class arming_screen {
private:
  weapons::armament const &inventory;
  resources::executable_tables const &tables;
  flight::airframe const &profile;
  resources::screen_image background;
  dac_palette palette;
  arming_controller controls;
  arming_preview preview;
  render::software_renderer renderer;
  double previous_drag{0};
  vec3<int16_t> previous_point{0,0,0};
  unsigned int fade_level{1};
  bool entering{true};
  bool leaving{false};
  uint8_t key{0};
  void draw(vec2<int16_t> const &position, vec2<int16_t> const &movement, uint8_t buttons);

public:
  arming_screen(resources::archive const &game, resources::executable_tables const &tables, weapons::armament &inventory,
    flight::player_aircraft aircraft, unsigned int default_fit);
  void press(uint8_t scan);
  bool advance(vec2<int16_t> const &position, vec2<int16_t> const &movement, uint8_t buttons);
  render::framebuffer const &image() const;
  render::palette colours() const;
};

} // namespace tfx::presentation
