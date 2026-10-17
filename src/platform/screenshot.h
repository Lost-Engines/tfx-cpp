#pragma once

#include "render/framebuffer.h"

namespace tfx::platform {

auto save_screenshot(std::filesystem::path const &directory,
  render::framebuffer const &image, render::dac_palette const &colours)->std::filesystem::path;

} // namespace tfx::platform
