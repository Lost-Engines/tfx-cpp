#include "auxiliary.h"
#include <stdexcept>
#include <utility>
#include "render/sprites.h"

namespace tfx::cockpit {

auxiliary_lamps::auxiliary_lamps(instrument_assets const &source, resources::archive const &game) : assets{source} {
  for(unsigned int bank{0}; bank != banks.size(); ++bank) banks[bank] = resources::decode_sprites(game.read(assets.auxiliary_banks[bank]));
}
auxiliary_animation const &auxiliary_lamps::state() const { return animation; }

void auxiliary_lamps::draw(render::framebuffer &target, auxiliary_state const &state, render::framebuffer *const coverage, render::raster_clip const &clip) {
  // Native 0x8046c..0x806b3, with the ammunition painter at 0x7e288.
  if(state.ammunition_pips > assets.ammunition_pips.size()) throw std::runtime_error{"too many native ammunition indicator pips"};
  auto const sprite{[&](unsigned int const bank, unsigned int const frame, vec2<int> const &position) {
    render::draw_sprite(target,banks.at(bank).at(frame),{static_cast<uint16_t>(position.x + state.offset.x),static_cast<uint16_t>(position.y + state.offset.y)},coverage,clip);
  }};
  unsigned int constexpr refresh_frames{3};
  if(std::to_underlying(state.engines[0]) != assets.engine_lamp_cache[0] || std::to_underlying(state.engines[1]) != assets.engine_lamp_cache[1] || state.redraw_phase == 2) animation.engine_refresh = refresh_frames;
  if(animation.engine_refresh) {
    sprite(0,state.engines[0] == flight::system_condition::active ? 0u : 1u,{20,165});
    sprite(0,state.engines[1] == flight::system_condition::active ? 0u : 1u,{28,165});
    --animation.engine_refresh;
  }
  // The original cache bytes above are read here but are not rewritten by this draw region.
  if(state.redraw_phase == 2) animation.ammunition_refresh = refresh_frames;
  if(animation.ammunition_refresh) {
    if(state.offset.y + 195 <= 198) for(unsigned int pip{0}; pip != state.ammunition_pips; ++pip) {
      auto const &position{assets.ammunition_pips[pip]};
      // CD889 consumes two independent colour/X/Y points, painting each as a 2x2 marker.
      // Horizontal overflow follows the native linear VGA address into the next row.
      for(unsigned int point{0}; point != 2; ++point) {
        unsigned int const x{static_cast<uint16_t>(position.x + state.offset.x + point * 2)};
        unsigned int const y{static_cast<uint16_t>(position.y + state.offset.y)};
        for(unsigned int row{0}; row != 2; ++row) for(unsigned int column{0}; column != 2; ++column) {
          unsigned int const destination{(y + row) * render::screen_width + x + column};
          if(destination >= target.pixels.size()) continue;
          target.pixels[destination] = 14;
          if(coverage) coverage->pixels[destination] = 255;
        }
      }
    }
    --animation.ammunition_refresh;
  }
  if(state.approach_cue && !state.approach_suppressed && *state.approach_cue < 3) {
    std::array<int,3> constexpr cue_rows{79,84,91};
    sprite(1,*state.approach_cue,{248,cue_rows[*state.approach_cue]});
  }
  if(state.low_speed_ground_contact) sprite(2,0,{75,78});
  if(state.landed) sprite(2,1,{75,90});
}

} // namespace tfx::cockpit
