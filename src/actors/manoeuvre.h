#pragma once

#include <array>
#include "math/native.h"
#include "resources/archive.h"

namespace tfx::actors {

unsigned int constexpr manoeuvre_header_bytes{16}, manoeuvre_step_bytes{6}, manoeuvres_per_bank{40};
struct manoeuvre {
  resources::bytes source;
  uint8_t category;
  vec2<math::angle> entry_angles;
  int16_t minimum_speed;
  int32_t relative_altitude;
  explicit manoeuvre(resources::bytes source);
};
struct manoeuvre_cursor {
  unsigned int program;
  unsigned int address{0};
};
std::vector<manoeuvre> load_manoeuvres(resources::archive const &game);

} // namespace tfx::actors
