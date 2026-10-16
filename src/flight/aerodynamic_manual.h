#pragma once

#include "flight/aerodynamic_airdata.h"
#include "flight/aerodynamic_controls.h"
#include "flight/aerodynamic_speed.h"
#include "flight/aerodynamic_surfaces.h"

namespace tfx::flight {

struct aerodynamic_manual_state {
  aerodynamic_control_state controls{};
  double elevator_trim{0};
  double pitch_rate_bias{0};
  double flap_fraction{0};
  double positive_g_lift_limit{0};
  double negative_g_lift_limit{0};
  double thrust_vector_fraction{0};
  double air_brake_fraction{0};
  system_condition air_brake_condition{system_condition::normal};
};
struct aerodynamic_manual_context {
  aerodynamic_airdata const &data;
  aerodynamic_coefficients const &coefficients;
  aerodynamic_surface_state const &surfaces;
  aerodynamic_surface_parameters const &geometry;
  player_aircraft aircraft{player_aircraft::eurofighter};
  control_source source{control_source::keyboard};
  double maximum_g{9};
  double minimum_g{-3};
  double cockpit_upward_metres{-.85344};
  double engine_pitch_arm{0};
  double body_down_force{0};
  double body_forward_force{0};
  double accumulated_damage{0};
  unsigned int afterburner_stages{0};
  bool military{false};
  bool stick_pressure{false};
  system_condition flaps_condition{system_condition::normal};
};

// Complete ordinary/manual 0x9ac9c path. Autopilot routing/attitude control
// selects a separate prefix; device input has already produced control targets.
afterburner_change update_aerodynamic_manual(aerodynamic_manual_state &state, aerodynamic_powerplant &powerplant, aerodynamic_manual_context const &context);

} // namespace tfx::flight
