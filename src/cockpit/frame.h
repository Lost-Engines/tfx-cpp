#pragma once

#include <optional>
#include "cockpit/instrument_assets.h"
#include "resources/archive.h"
#include "resources/compiled_overlay.h"

namespace tfx::cockpit {

class frame {
private:
  struct artwork {
    std::optional<resources::indexed_image> panel;
    std::optional<resources::compiled_overlay> overlay;
  };
  instrument_assets const &assets;
  std::array<artwork,viewport_count> views;

public:
  frame(instrument_assets const &assets, resources::archive const &game);
  vec2<int16_t> clamp(unsigned int view, vec2<int16_t> const &offset) const;
  vec2d projection_origin(unsigned int view, vec2<int16_t> const &offset) const;
  void paint(render::framebuffer &target, unsigned int view, vec2<int16_t> const &offset, render::framebuffer *coverage = nullptr) const;
};

enum class cockpit_motion { idle, up, down };
class cockpit_position {
private:
  instrument_assets const &assets;
  vec2<int16_t> offset;
  unsigned int step{0};
  cockpit_motion motion{cockpit_motion::idle};

public:
  cockpit_position(instrument_assets const &assets, vec2<int16_t> const &offset);
  vec2<int16_t> const &value() const;
  unsigned int step_index() const;
  cockpit_motion movement() const;
  void raise();
  void lower();
  void advance(int16_t viewport_bottom);
};

} // namespace tfx::cockpit
