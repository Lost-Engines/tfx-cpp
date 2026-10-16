#include "aerodynamic_commands.h"
#include "math/floating_environment.h"
#include "math/x87.h"

namespace tfx::flight {
namespace {

using calculation = long double;
double constexpr minimum_command_speed{1}, native_pi{3.14159};
double constexpr thrust_vector_degrees{20}, native_inverse_degrees{.005555555555555555};
// Binary64 constant evaluation preserves the original 53-bit intermediate
// products; folding these as long double would silently use 64-bit precision.
double constexpr maximum_vector_angle{native_pi * thrust_vector_degrees * native_inverse_degrees};
double constexpr vector_moment_multiplier{2}, pitch_rate_divisor{2}, roll_rate_multiplier{-2};

calculation wide(double const value) { return value; }

} // anonymous namespace

void update_aerodynamic_commands(aerodynamic_commands &state, aerodynamic_manual_state const &manual, aerodynamic_powerplant const &powerplant, aerodynamic_command_context const &context) {
  math::floating_environment const environment;
  auto const &data{context.data};
  auto const &geometry{context.geometry};
  auto const &coefficients{context.coefficients};
  if(data.metres_per_second <= minimum_command_speed) {
    state.angle_of_attack = data.angle_of_attack;
    return;
  }
  auto const alpha{wide(data.angle_of_attack)};
  state.body_lift_force = static_cast<double>(math::x87::sin(alpha) * context.body_forward_force - math::x87::cos(alpha) * context.body_down_force);
  auto const vector_sine{math::x87::sin(wide(maximum_vector_angle))};
  calculation const pitch_thrust{wide(powerplant.thrust) * manual.thrust_vector_fraction * vector_sine * context.engine_pitch_arm * vector_moment_multiplier};
  calculation const dynamic_area{wide(data.atmosphere.density) * data.metres_per_second * data.metres_per_second * geometry.wing_area};
  calculation const pitch_control{pitch_thrust / (dynamic_area * geometry.mean_chord) + wide(coefficients.elevator_moment) * geometry.maximum_elevator_angle};
  // The simplified law explicitly constructs zero pitch rate. Keep the
  // original arithmetic, including its sign, damping term and store boundary.
  calculation const zero_damping{0.0L / (wide(data.mass_kg) * data.metres_per_second) * coefficients.pitch_damping * geometry.mean_chord};
  state.angle_of_attack = static_cast<double>(-(pitch_control * manual.controls.elevator + geometry.zero_pitch_moment + zero_damping / (wide(data.metres_per_second) * pitch_rate_divisor)) / coefficients.pitch_stability);
  if(context.stick_pressure) state.angle_of_attack = static_cast<double>(wide(context.seconds) * manual.pitch_rate_bias + state.angle_of_attack);
  calculation const roll_thrust{wide(powerplant.thrust) * manual.thrust_vector_fraction * vector_sine * context.engine_roll_arm * vector_moment_multiplier};
  calculation const roll_control{roll_thrust / (dynamic_area * geometry.wing_span) + wide(coefficients.aileron_effectiveness) * geometry.maximum_aileron_angle};
  state.roll_rate = static_cast<double>(wide(data.metres_per_second) * roll_rate_multiplier / (wide(geometry.wing_span) * coefficients.roll_damping) * manual.controls.aileron * roll_control);
}

} // namespace tfx::flight
