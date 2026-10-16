#pragma once

#include <array>
#include <string>
#include "resources/media.h"

namespace tfx::cockpit {

enum class instrument_mask : unsigned int { store, throttle, fuel, gear, left_flap, right_flap, lower_flap, left_engine, right_engine, count };

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
  std::string display_bank;
  std::array<vec2<int16_t>,3> display_origins;
  std::array<resources::monochrome_image,static_cast<unsigned int>(instrument_mask::count)> masks;
  std::array<std::array<uint8_t,10>,3> store_order;
  std::array<std::array<vec2<int16_t>,10>,3> store_positions;
  std::array<vec2<int16_t>,12> system_positions;
  std::array<std::array<vec2<int16_t>,2>,12> system_boxes;
  std::array<std::string,12> system_labels;
  std::array<std::array<vec2<int16_t>,2>,4> fuel_cells;
  std::array<std::string,3> flight_formats;
  std::string zero_range;
  std::array<std::string,2> engine_formats;
  std::string fuel_total_format;
  float speed_scale;
  float altitude_scale;
  double gauge_fuel_scale;
  float gauge_throttle_scale;
  double engine_percent;
  explicit instrument_assets(std::span<uint8_t const> executable);
};

} // namespace tfx::cockpit
