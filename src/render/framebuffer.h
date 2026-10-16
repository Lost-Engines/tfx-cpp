#pragma once

#include <array>
#include <filesystem>
#include <span>
#include <vector>
#include "vectorstorm/vector/vector4.h"
#include "math/native.h"

namespace tfx::render {

int constexpr screen_width{320}, screen_height{200};
int constexpr display_width{320}, display_height{240};
int constexpr centre_x{screen_width / 2}, centre_y{screen_height / 2};
double constexpr focal_length{128};
using palette = std::array<vec3<uint8_t>, 256>;
using dac_palette = std::array<uint8_t,256 * 3>;
using rgba_pixel = vec4<uint8_t>;
static_assert(sizeof(rgba_pixel) == 4);

struct framebuffer {
  std::array<uint8_t, screen_width * screen_height> pixels{0};
  std::vector<rgba_pixel> colourise(palette const &colours) const;
  void screenshot(std::filesystem::path const &path, palette const &colours) const;
};

palette decode_palette(std::span<uint8_t const> source);
palette expand_dac_palette(dac_palette const &source);

} // namespace tfx::render
