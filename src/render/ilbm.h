#pragma once

#include "render/framebuffer.h"

namespace tfx::render {

// Original 4-key captures are eight-plane IFF images. Keep VGA indices and
// the displayed six-bit DAC values; the host window's RGB scaling is separate.
auto encode_ilbm(framebuffer const &image, dac_palette const &colours)->std::vector<uint8_t>;

} // namespace tfx::render
