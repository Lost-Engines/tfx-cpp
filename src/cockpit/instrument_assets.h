#pragma once

#include <array>
#include <string>
#include "resources/media.h"
#include "cockpit/viewport_layout.h"

namespace tfx::cockpit {

enum class instrument_mask : unsigned int { store, throttle, fuel, gear, left_flap, right_flap, lower_flap, left_engine, right_engine, target_reticle, alternate_target_reticle, short_range_sight, medium_range_sight, long_range_sight, ground_sight, strafe_sight, weapon_centre_cue, impact_sight, count };

struct radar_scale {
  int16_t label;
  int16_t world_per_pixel;
};

struct pitch_mark {
  int16_t label;
  bool dashed;
  std::array<vec2<int16_t>,6> vertices;
};

struct instrument_assets {
  std::array<uint8_t,64> character_map;
  std::string font_bank;
  std::string heading_bank;
  std::string pitch_bank;
  std::array<pitch_mark,42> pitch_marks;
  std::string in_range_label;
  std::string aiming_bank;
  std::array<std::string,7> aiming_labels;
  std::array<std::string,3> brake_messages;
  std::array<std::string,5> hud_number_formats;
  float hud_altitude_scale;
  float hud_throttle_scale;
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
  std::string controls_bank;
  std::string autopilot_bank;
  std::string autopilot_number_format;
  std::string autopilot_label;
  std::array<std::string,5> autopilot_mode_labels;
  std::array<std::string,5> configuration_labels;
  std::string autopilot_height_speed_format;
  std::string autopilot_speed_format;
  double surface_scale;
  double raptor_degrees;
  double raptor_radians;
  double raptor_pointer_scale;
  double autopilot_speed_scale;
  double autopilot_height_scale;
  std::string radar_bank;
  std::string radar_format;
  std::array<radar_scale,4> horizontal_scales;
  std::array<radar_scale,3> bvr_scales;
  std::array<vec2<int16_t>,40> bvr_envelope;
  std::array<std::string,2> warning_banks;
  std::array<uint8_t,15> condition_frames;
  std::array<std::string,3> auxiliary_banks;
  std::array<uint8_t,2> engine_lamp_cache;
  std::array<vec2<int16_t>,4> afterburner_pips;
  std::array<vec2<int16_t>,3> display_origins;
  std::array<vec2<int16_t>,3> display_sizes;
  int16_t camera_blink;
  vec3<math::angle> camera_orbit_angles;
  int16_t camera_orbit_step;
  vec2<int32_t> camera_height_bounds;
  std::string ground_range_format;
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
  std::array<viewport_layout,viewport_count> viewports;
  std::array<int16_t,22> cockpit_steps;
  explicit instrument_assets(std::span<uint8_t const> executable);
};

} // namespace tfx::cockpit
