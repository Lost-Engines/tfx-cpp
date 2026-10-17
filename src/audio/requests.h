#pragma once

#include <array>
#include <cstdint>
#include <utility>

namespace tfx::audio {

enum class music_cue_id : uint8_t {
  mission_start,
  aircraft_lost,
  normal_flight,
  mission_complete,
  unauthorised_target = 5,
  ejection = 6,
  landing_approach,
  damaged_landing_approach,
  incoming_projectile,
  player_aircraft_kill,
  engines = 12,
};
enum class sample_id : unsigned int {
  gear = 1,
  afterburner_stop = 8,
  control_selection = 8,
  weapon_release = 11,
  aircraft_explosion = 12,
  cannon_fire = 13,
  cannon_hit = 14,
  nearby_flak = 16,
  ejection = 20,
  mission_complete = 41,
  unauthorised_target = 42,
  threat = 43,
  refuel_acquiring = 46,
  refuel_response = 48,
  landing_stopped = 49,
  recovery = 62,
  bomb_release = 64,
  fill_up = 69,
  mayday = 72,
  missile_release = 73,
  afterburner = 75,
};

// Native 0x8bd8c/0xa4f10: the shared release sound followed by the
// weapon-class sample. Categories outside this authored bomb set use missile.
constexpr std::array<unsigned int,2> store_release_sequence(uint8_t const category) {
  bool const bomb{category == 3 || category == 5 || category == 7 || category == 9};
  return {std::to_underlying(sample_id::weapon_release),std::to_underlying(bomb ? sample_id::bomb_release : sample_id::missile_release)};
}

} // namespace tfx::audio
