#include "hud_text.h"
#include <cmath>
#include <cstdio>
#include <stdexcept>

namespace tfx::cockpit {
namespace {

template<typename Value>
std::string formatted(std::string const &format, Value const value) {
  std::array<char,128> buffer{};
  int const length{std::snprintf(buffer.data(),buffer.size(),format.c_str(),value)};
  if(length < 0 || static_cast<unsigned int>(length) >= buffer.size()) throw std::runtime_error{"HUD readout exceeds its display buffer"};
  std::string result{buffer.data(),static_cast<unsigned int>(length)};
  return result;
}

std::string decimal(std::string const &format, double const value, unsigned int const precision) {
  // Watcom rounds the stored double after multiplying by 10^precision.
  // Its rounded decimal zero has no sign. Host printf instead rounds the
  // exact binary fraction: e.g. it prints 0.005 as "0.01", rather than "0.00".
  double const scale{precision == 2 ? 100.0 : precision == 1 ? 10.0 : 1.0};
  double const rounded{std::nearbyint(value * scale)};
  return formatted(format,rounded == 0 ? 0.0 : rounded / scale);
}

} // anonymous namespace

hud_text::hud_text(instrument_assets const &source) : assets{source} {
}
void hud_text::draw(render::software_renderer &renderer, hud_text_state const &state, render::framebuffer *const coverage) const {
  uint8_t constexpr colour{6};
  auto const text{[&](vec2<int> const &local, std::string const &message) {
    int const x{math::signed_word(static_cast<uint16_t>(local.x + state.offset.x))};
    int const y{math::signed_word(static_cast<uint16_t>(local.y + state.offset.y))};
    renderer.text(x,y,message,colour,coverage);
  }};
  auto const right{[&](vec2<int> const &edge, std::string const &message) {
    text({math::signed_word(static_cast<uint16_t>(edge.x - renderer.text_width(message))),edge.y},message);
  }};
  // Native 0x7f8e0: every formatted product crosses its original double store.
  text({98,54},decimal(assets.hud_number_formats[0],static_cast<double>(-static_cast<long double>(state.height) * assets.hud_altitude_scale),0));
  text({204,54},decimal(assets.hud_number_formats[0],static_cast<double>(static_cast<long double>(state.speed) * assets.speed_scale),0));
  text({204,63},decimal(assets.hud_number_formats[1],state.mach,2));
  right({230,80},decimal(assets.hud_number_formats[2],static_cast<double>(state.load),1));
  int constexpr world_units_per_cell{2048};
  right({217,86},formatted(assets.hud_number_formats[3],static_cast<long>(state.position.x / world_units_per_cell)));
  right({230,86},formatted(assets.hud_number_formats[3],static_cast<long>(state.position.z / world_units_per_cell)));
  text({96,79},decimal(assets.hud_number_formats[4],static_cast<double>(static_cast<long double>(state.throttle) * assets.hud_throttle_scale),0));
  // Native 0x7eb7c: the three messages have independent eligibility and rows.
  std::array<bool,3> const enabled{state.air_brake,state.brake_chute,state.arrester_cable};
  int constexpr message_first_row{29}, message_spacing{7};
  for(unsigned int index{0}; index != enabled.size(); ++index) if(enabled[index]) {
    auto const &message{assets.brake_messages[index]};
    int const width{math::signed_word(static_cast<uint16_t>(renderer.text_width(message)))};
    text({render::centre_x - width / 2,message_first_row + static_cast<int>(index) * message_spacing},message);
  }
}

} // namespace tfx::cockpit
