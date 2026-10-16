#pragma once

#include "flight/aerodynamic_manual.h"

namespace tfx::flight {

struct aerodynamic_commands {
  double roll_rate{0};
  double angle_of_attack{0};
  double body_lift_force{0};
};
struct aerodynamic_command_context {
  aerodynamic_airdata const &data;
  aerodynamic_coefficients const &coefficients;
  aerodynamic_surface_parameters const &geometry;
  double engine_roll_arm{0};
  double engine_pitch_arm{0};
  double body_forward_force{0};
  double body_down_force{0};
  double seconds{.02};
  bool stick_pressure{false};
};

// Native 0x99f6f..0x9a100, after input/manual control: Realistic converts the
// aerodynamic derivatives and controls into commanded attitude changes.
void update_aerodynamic_commands(aerodynamic_commands &state, aerodynamic_manual_state const &manual, aerodynamic_powerplant const &powerplant, aerodynamic_command_context const &context);

} // namespace tfx::flight
