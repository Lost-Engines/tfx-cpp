#pragma once

#include "flight/aircraft.h"

namespace tfx::flight {

// Shared original Arcade/Simple aircraft coefficients. The full aerodynamic
// models have additional tables; these are the basic-model preset consumers.
struct basic_aircraft_parameters {
  float low_stall_mach;
  float low_altitude;
  float middle_stall_mach;
  float middle_altitude;
  float high_stall_mach;
  float ceiling_km;
  float high_maximum_mach;
  float maximum_speed_altitude;
  float low_maximum_mach;
  float maximum_speed_base_altitude;
  float gear_height;
  double stall_metres_per_second;
  double fuel_capacity;
  double dry_thrust_fraction;
  uint8_t afterburner_stages;
  double maximum_g;
  double minimum_g;
  double low_speed_reference;
  double gear_airborne_speed_limit;
  double gear_ground_speed_limit;
  double gear_touchdown_descent_limit;
};

basic_aircraft_parameters const &basic_parameters(player_aircraft aircraft);

} // namespace tfx::flight
