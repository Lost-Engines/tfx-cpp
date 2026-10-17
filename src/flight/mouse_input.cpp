#include "mouse_input.h"

namespace tfx::flight {

vec2<int16_t> mouse_flight_input::advance(vec2<int16_t> const &mickeys) {
  int16_t constexpr lower{-512}, upper_exclusive{512};
  // The original lower/upper passes each clamp at most one axis. Retain those
  // else branches, including a temporarily out-of-range Y when both axes cross.
  if(position.x < lower) position.x = lower;
  else if(position.y < lower) position.y = lower;
  if(position.x >= upper_exclusive) position.x = upper_exclusive - 1;
  else if(position.y >= upper_exclusive) position.y = upper_exclusive - 1;
  for(unsigned int axis{0}; axis != 2; ++axis) position[axis] = math::signed_word(static_cast<uint16_t>(position[axis] + mickeys[axis]));
  return vec2<int16_t>{position};
}

} // namespace tfx::flight
