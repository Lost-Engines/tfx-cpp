#pragma once

#include <string>
#include <vector>
#include "resources/binary.h"

namespace tfx::weapons {

enum class weapon_id : uint8_t { cannon, sidewinder_s, sidewinder_l, asraam, amraam, aaam, aa_arm, fuel_tank, mk82, gbu10, gbu24, gbu16, gbu12, gbu24_blu, cbu55, jp233, csw, durandal, maverick, agm109, harm, sidearm, harpoon, submunition, chaff, flare, cargo };
unsigned int constexpr weapon_count{27};
enum class flight_stage {
  finished, attached, falling, accelerating, coasting, guided, sea_skimming,
  falling_store, retarded_store, attached_dispenser, falling_dispenser, decoyed, accelerating_alias,
};
struct stage {
  uint16_t ticks;
  flight_stage motion;
};
struct definition {
  std::string label{};
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
