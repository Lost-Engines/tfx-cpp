#pragma once

#include "flight/aerodynamic_manual.h"

namespace tfx::flight {

// Native 0x9bfa5 onward, shared by manual and autopilot prefixes.
afterburner_change finish_aerodynamic_controls(aerodynamic_manual_state &state, aerodynamic_powerplant &powerplant, aerodynamic_manual_context const &context);

} // namespace tfx::flight
