#pragma once

#include "flight/aerodynamic.h"
#include "flight/simple.h"

namespace tfx::flight {

// Native player callbacks share view, engine, fuel and undercarriage globals,
// but retain separate basic-model speed/altitude/control caches. Transfer only
// those shared values at callback boundaries; do not derive basic caches from
// physical air data when autopilot temporarily selects an advanced callback.
void capture_shared_player(aerodynamic_flight &physical, simple_state const &basic, damage_state const &damage, bool simple_body);
void publish_shared_player(simple_state &basic, aerodynamic_flight const &physical);

} // namespace tfx::flight
