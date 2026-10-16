#include "arming_screen.h"
#include <algorithm>
#include <utility>

namespace tfx::presentation {

arming_screen::arming_screen(resources::archive const &game, resources::executable_tables const &tables, weapons::armament &inventory,
  flight::player_aircraft const aircraft, unsigned int const default_fit) :
  inventory{inventory}, tables{tables}, profile{tables.airframes.at(std::to_underlying(aircraft) - 1)},
  controls{inventory,tables.arming_art(),default_fit}, preview{game,tables,aircraft}, renderer{tables} {
  auto const bytes{game.read("iff/raw/" + tables.arming_art().backdrop)};
  background = resources::decode_screen(bytes);
  std::ranges::copy(resources::binary_view{bytes}.slice(4,palette.size()),palette.begin());
  // The original prepares both display pages before the forty-retrace fade-in.
  draw({100,75},{0,0},0);
  draw({100,75},{0,0},0);
}
void arming_screen::draw(vec2<int16_t> const &position, vec2<int16_t> const &movement, uint8_t const buttons) {
  std::optional<unsigned int> picked;
  auto const mode{controls.state().mode};
  if(mode == arming_mode::placing || mode == arming_mode::clearing) {
    auto const point{arming_preview::pointer_point(position)};
    picked = preview.pick(previous_point,point);
    previous_point = point;
  }
  renderer.output = background.image;
  preview.draw_models(renderer,controls.state(),inventory,controls.previews());
  previous_drag = draw_arming_widgets(renderer,tables.arming_art(),controls.state(),inventory,tables.weapons,profile,previous_drag).drag;
  if(mode == arming_mode::unavailable) draw_arming_unavailable(renderer,tables.arming_art());
  if(mode == arming_mode::overview) for(unsigned int slot{0}; slot != flight::store_slots; ++slot) {
    auto const &store{inventory.pylons[slot]};
    if(store.weapon != weapons::empty_pylon && store.count) draw_arming_store_label(renderer,tables.weapons[store.weapon].label,vec2<int>{tables.arming_art().slot_labels[slot]});
  }
  if(mode == arming_mode::clearing && picked) {
    auto const &store{inventory.pylons[*picked]};
    if(store.weapon != weapons::empty_pylon && store.count) draw_arming_store_label(renderer,tables.weapons[store.weapon].label,{30,160});
  }
  controls.advance(position,movement,buttons,picked);
  preview.draw_cursor(renderer,controls.state(),position);
}
void arming_screen::press(uint8_t const scan) { key = scan; }
bool arming_screen::advance(vec2<int16_t> const &position, vec2<int16_t> const &movement, uint8_t const buttons) {
  if(entering) {
    if(fade_level < 40) ++fade_level;
    else { entering = false;preview.start(); }
    return false;
  }
  if(leaving) {
    if(fade_level) --fade_level;
    return fade_level == 0;
  }
  controls.press(std::exchange(key,0));
  preview.advance();
  draw(position,movement,buttons);
  if(controls.state().mode == arming_mode::complete) leaving = true;
  return false;
}
render::framebuffer const &arming_screen::image() const { return renderer.output; }
render::palette arming_screen::colours() const { return render::decode_palette(fade_palette(palette,fade_level,40)); }

} // namespace tfx::presentation
