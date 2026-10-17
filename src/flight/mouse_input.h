#pragma once

#include "math/native.h"

namespace tfx::flight {

struct mouse_flight_input {
  vec2<int16_t> position{0,0};
  // Native 0x7459c then 0x74508: constrain the previous virtual stick position,
  // then accumulate this frame's relative mickeys with signed-word wrapping.
  vec2<int16_t> advance(vec2<int16_t> const &mickeys);
};

} // namespace tfx::flight
