#pragma once

#include "flight/aerodynamic_ground.h"

namespace tfx::flight {

// Shared native carrier cable stage; Realistic omits the physical hook moment.
void update_aerodynamic_arrestor(aerodynamic_ground_state &state, aerodynamic_motion const &motion, aerodynamic_ground_parameters const &parameters, aerodynamic_ground_context const &context, bool apply_moments);

} // namespace tfx::flight
