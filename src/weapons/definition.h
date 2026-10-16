#pragma once

#include <string>
#include <vector>
#include "resources/binary.h"

namespace tfx::weapons {

unsigned int constexpr weapon_count{27};
enum class flight_stage {
  finished, attached, falling, accelerating, coasting, guided, sea_skimming,
  falling_store, retarded_store, attached_dispenser, falling_dispenser, decoyed,
};
struct stage {
  uint16_t ticks;
  flight_stage motion;
};
struct definition {
  std::string carried;
  std::string fired;
  std::string secondary;
  uint8_t category;
  int16_t mass;
  int32_t range;
  int16_t launch_speed;
  std::vector<stage> stages;
};
std::vector<definition> load_definitions(std::span<uint8_t const> executable);

} // namespace tfx::weapons
