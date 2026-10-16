#pragma once

#include "flight/aerodynamic_forces.h"

namespace tfx::flight {

struct aerodynamic_response_parameters {
  double wing_area{0};
  double wing_span{0};
  double mean_chord{0};
  double maximum_aileron_radians{0};
  double rudder_effectiveness{.3};
  double roll_damping{0};
  double pitch_damping{0};
  double pitch_stability{0};
  double zero_pitch_moment{0};
  double roll_thrust_arm{0};
  double pitch_thrust_arm{0};
};
struct aerodynamic_response_state {
  aerodynamic_motion motion{};
  double sideslip_radians{0};
  double previous_pitch_rate{0};
  bool low_speed_ground_contact{false};
  float g_load{0};
};
struct aerodynamic_response_context {
  aerodynamic_basis basis{};
  aerodynamic_inertia inertia{};
  aerodynamic_response_parameters parameters{};
  double seconds{.02};
  double metres_per_second{0};
  double density{0};
  double stall_metres_per_second{0};
  double rudder{0};
  double aileron{0};
  double elevator{0};
  double roll_control_gradient{0};
  double pitch_control_gradient{0};
  double engine_thrust{0};
  double thrust_moment_scale{0};
  double angle_of_attack{0};
  double pitch_rate_bias{0};
  double ground_vertical_force{0};
  bool time_warp{false};
  bool landed{false};
  bool autopilot{false};
  bool rudder_inhibited{false};
  bool realistic{false};
  bool stick_pressure{false};
};

// Native 0x9f41c advances velocity/rates, applies rudder and ground handling,
// then retains the original stiff roll/pitch damping fallbacks and yaw cap.
void update_aerodynamic_response(aerodynamic_response_state &state, aerodynamic_response_context const &context);

} // namespace tfx::flight
