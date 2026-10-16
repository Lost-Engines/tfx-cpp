#pragma once

#include <array>
#include <string>
#include "resources/binary.h"

namespace tfx::cockpit {

struct instrument_assets {
  std::array<uint8_t,64> character_map;
  std::string font_bank;
  std::array<std::string,2> unsigned_clock_formats;
  std::array<std::string,2> signed_clock_formats;
  std::string fuel_format;
  double critical_fuel;
  double low_fuel;
  std::array<std::string,3> throttle_formats;
  float throttle_percent;
  std::string ecm_label;
  std::string stealth_label;
  std::array<std::string,2> decoy_formats;
  explicit instrument_assets(std::span<uint8_t const> executable);
};

} // namespace tfx::cockpit
