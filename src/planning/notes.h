#pragma once

#include <map>
#include "presentation/widget_font.h"

namespace tfx::planning {

struct annotation {
  uint8_t waypoint;
  uint8_t route;
  vec2<uint8_t> position;
  vec2<uint8_t> size;
  std::string text;
};
class notes {
private:
  std::map<uint16_t,annotation> entries;

public:
  explicit notes(std::string_view source);
  annotation const *find(uint8_t waypoint, uint8_t route = 255) const;
  std::map<uint16_t,annotation> const &all() const;
};

void draw_annotation(render::framebuffer &image, presentation::widget_font const &font,
  annotation const &note);

} // namespace tfx::planning
