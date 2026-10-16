#pragma once

#include "flight/aircraft.h"

namespace tfx::flight {

struct aerodynamic_coefficient_parameters {
  double base_drag{0};
  double critical_mach{.95};
  double full_wave_drag_mach{1.1};
  double wave_drag_increment{0};
  double wing_area{0};
  double additional_lifting_area{0};
  double pitch_stability_base{0};
  double pitch_stability_correction{0};
  double pitch_damping_mach_gradient{0};
  double pitch_damping_base{0};
  double elevator_moment_gradient{0};
  double elevator_lift_gradient{0};
  double roll_damping_gradient{0};
  double aileron_gradient{0};
};
struct aerodynamic_coefficients {
  double reference_drag{0};
  double wave_drag{0};
  double zero_lift_drag{0};
  double lift_slope{0};
  double pitch_stability{0};
  double pitch_damping{0};
  double elevator_moment{0};
  double elevator_lift{0};
  double roll_damping{0};
  double roll_sideslip{0};
  double aileron_effectiveness{0};
};

// Native 0x99bc0: transonic drag and aircraft-specific Mach lift curves,
// followed by the original pitch, elevator-lift, roll and aileron derivatives.
aerodynamic_coefficients update_aerodynamic_coefficients(player_aircraft aircraft, double mach, aerodynamic_coefficient_parameters const &parameters);

} // namespace tfx::flight
