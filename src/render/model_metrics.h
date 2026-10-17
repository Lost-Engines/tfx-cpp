#pragma once

#include "math/native.h"

namespace tfx::render {

struct model_metrics {
  int16_t distance;
  int16_t order;
  uint8_t colour_row;
};
// Native BA98D/BB107 range and CC159 priority from cached Q15 products.
model_metrics measure_model(vec3<int32_t> const &camera_origin, int16_t sort_bias);

} // namespace tfx::render
