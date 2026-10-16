#pragma once

#include <string>
#include "math/native.h"

namespace tfx::cockpit {

struct viewport_layout {
  int16_t projection_centre_y;
  std::string panel;
  std::string overlay;
  int16_t bottom;
  unsigned int callback_file;
};
unsigned int constexpr viewport_count{29}, forward_cockpit{0};

} // namespace tfx::cockpit
