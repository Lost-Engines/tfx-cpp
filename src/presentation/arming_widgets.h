#pragma once

#include "presentation/arming_controller.h"
#include "flight/airframes.h"
#include "render/software_renderer.h"

namespace tfx::presentation {

flight::store_effects draw_arming_widgets(render::software_renderer &renderer, arming_assets const &assets,
  arming_state const &state, weapons::armament const &inventory, std::span<weapons::definition const> weapons,
  flight::airframe const &profile, double previous_drag);

} // namespace tfx::presentation
