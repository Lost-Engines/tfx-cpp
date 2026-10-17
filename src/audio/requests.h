#pragma once

#include <cstdint>

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
  aircraft_explosion = 12,
  cannon_hit = 14,
  ejection = 20,
  mission_complete = 41,
  unauthorised_target = 42,
  threat = 43,
  refuel_acquiring = 46,
  refuel_response = 48,
  landing_stopped = 49,
  recovery = 62,
  fill_up = 69,
  mayday = 72,
  afterburner = 75,
};

} // namespace tfx::audio
