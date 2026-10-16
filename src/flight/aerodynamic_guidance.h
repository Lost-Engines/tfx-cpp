#pragma once

#include "flight/aerodynamic_manual.h"
#include "flight/aerodynamic_recovery.h"
#include "flight/aerodynamic_rotation_internal.h"

namespace tfx::flight {

struct aerodynamic_guidance {
  double heading_error{0};
  double ground_speed{0};
  double climb_speed_limit{0};
  double requested_vertical_speed{0};
  double desired_flight_path{0};
  double actual_flight_path{0};
  double maximum_bank{0};
  double desired_bank{0};
  double roll_angle{0};
  double roll_error{0};
  double roll_control_rate{0};
  double commanded_roll_rate{0};
  double saved_roll_rate{0};
  double yaw_demand{0};
};
struct aerodynamic_guidance_context {
  aerodynamic_manual_context const &law;
  aerodynamic_powerplant_parameters const &engine;
  double seconds{.02};
  double roll_moment{0};
  double pitch_moment{0};
  double previous_drag{0};
  double rudder_effectiveness{.3};
  bool followed_aircraft{false};
  bool time_warp{false};
  aerodynamic_recovery_context recovery{};
};
struct aerodynamic_guidance_events {
  std::vector<afterburner_change> afterburner{};
  aerodynamic_recovery_change recovery{aerodynamic_recovery_change::none};
};

// Native 0x9b003..0x9bb20, after target/route selection: constrained heading,
// altitude, bank and pitch requests, overshoot attitude snaps and speed control.
aerodynamic_guidance_events update_aerodynamic_guidance(aerodynamic_guidance &state, aerodynamic_manual_state &manual, aerodynamic_powerplant &powerplant, aerodynamic_motion &motion, aerodynamic_recovery_state &recovery, aerodynamic_guidance_context const &context);


// Native 0x9bb20..0x9bce9 path to the common suffix: convert guidance rate
// requests to actual/keyboard elevator, aileron, rudder and aircraft trim.
void apply_aerodynamic_guidance(aerodynamic_guidance const &state, aerodynamic_manual_state &manual, aerodynamic_powerplant const &powerplant, aerodynamic_guidance_context const &context);

} // namespace tfx::flight
