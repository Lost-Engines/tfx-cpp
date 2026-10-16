#pragma once

#include "resources/binary.h"
#include "render/framebuffer.h"

namespace tfx::resources {

struct screen_overlay {
  render::framebuffer image;
  render::framebuffer coverage;
  void paint(render::framebuffer &target) const;
};

// The planner's panel was compiled into a fixed VGA painting stream in TFX.DAT.
// Decode that restricted artwork representation into indexed pixels, without executing game code.
screen_overlay decode_planner_panel(std::span<uint8_t const> executable);
std::array<uint8_t,256 * 3> planner_palette(std::span<uint8_t const> map_colours, std::span<uint8_t const> executable);

} // namespace tfx::resources
