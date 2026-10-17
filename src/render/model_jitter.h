#pragma once

#include "math/native.h"

namespace tfx::render {

class model_jitter {
private:
  math::jitter_state working;
  math::jitter_state saved;
public:
  explicit model_jitter(math::jitter_state initial = {});
  // Original C488D runs for every world viewport, including instrument views.
  void begin(bool animation_enabled);
  math::jitter_state &state();
};

} // namespace tfx::render
