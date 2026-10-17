#pragma once

#include "flight/control_input.h"

namespace tfx::flight {

struct keyboard_input {
  direction_keys directions;
  bool home{false};
  bool end{false};
  bool page_up{false};
  bool page_down{false};
  bool accelerate{false};
  bool decelerate{false};
  bool o{false};
  bool right_shift{false};
  bool control{false};
  bool automatic_landing{false};
};
struct keyboard_state {
  direction_keys directions;
  bool accelerate{false};
  bool decelerate{false};
  bool o_held{false};
  uint8_t view_pan{0};
  uint8_t target_pan{0};
};

// Original 0x862f4/0x86458 retain the manual flags while right Shift, Ctrl
// or automatic landing suspends their refresh. Left Shift is independent.
auto poll_keyboard(keyboard_state &state, keyboard_input const &input)->void;

} // namespace tfx::flight
