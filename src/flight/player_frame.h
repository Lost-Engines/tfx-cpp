#pragma once

#include "flight/aerodynamic.h"
#include "flight/fuel_gauge.h"

namespace tfx::flight {

struct player_frame_context {
  vec3f const &previous_position;
  simulation::timer_ticks elapsed{0};
  int16_t ground_elevation_steps{0};
  bool terrain_present{false};
};

// Native outer-player tail 0x8f98c..0x8fac4. Acknowledges callback resets,
// clamps only the float view height, updates engine/fuel indicators and returns
// measured movement in Q8 world units per native tick. Integer view coordinates
// and the physical NED position deliberately retain their callback values.
int32_t finish_player_frame(aerodynamic_flight &flight, damage_state &damage, fuel_gauge &fuel, player_frame_context const &context);

} // namespace tfx::flight
