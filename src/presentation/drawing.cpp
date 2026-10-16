#include "drawing.h"
#include <algorithm>
#include <cstdlib>

namespace tfx::presentation {

// Native widgets use inclusive endpoints and the same Bresenham tie rule as VGA lines.
void draw_line(render::framebuffer &image, vec2<int> from, vec2<int> const &to, uint8_t const colour) {
  if(from.x > to.x) { draw_line(image,vec2<int>{to},from,colour);return; }
  int const dx{to.x - from.x}, dy{std::abs(to.y - from.y)}, direction{from.y <= to.y ? 1 : -1};
  auto const pixel{[&] {
    if(from.x >= 0 && from.x < render::screen_width && from.y >= 0 && from.y < render::screen_height) image.pixels[from.y * render::screen_width + from.x] = colour;
  }};
  int error{std::max(dx,dy) / 2};
  for(int step{0}; step <= std::max(dx,dy); ++step) {
    pixel();
    if(dx > dy) {
      ++from.x;
      error -= dy;
      if(error < 0) { from.y += direction;error += dx; }
    } else {
      from.y += direction;
      error -= dx;
      if(error < 0) { ++from.x;error += dy; }
    }
  }
}

void draw_clipped_line(render::framebuffer &image, vec2<int> from, vec2<int> to,
  vec2<int> const &minimum, vec2<int> const &maximum, uint8_t const colour) {
  // Clip X before Y. Native 0xbf53d measures from the nearer endpoint so its
  // truncating divisions do not move a clipped edge by a pixel unnecessarily.
  auto const move{[](int &value, int &other, int const target, int const end, int const end_other) {
    int const distance{std::abs(target - value)}, remainder{std::abs(end - target)}, total{std::abs(end - value)};
    if(total) other = distance <= remainder ? other + (end_other - other) * distance / total : end_other - (end_other - other) * remainder / total;
    value = target;
  }};
  for(unsigned int axis{0}; axis != 2; ++axis) {
    if(std::max(from[axis],to[axis]) < minimum[axis] || std::min(from[axis],to[axis]) > maximum[axis]) return;
    if(from[axis] < minimum[axis]) move(from[axis],from[1 - axis],minimum[axis],to[axis],to[1 - axis]);
    if(to[axis] < minimum[axis]) move(to[axis],to[1 - axis],minimum[axis],from[axis],from[1 - axis]);
    if(from[axis] > maximum[axis]) move(from[axis],from[1 - axis],maximum[axis],to[axis],to[1 - axis]);
    if(to[axis] > maximum[axis]) move(to[axis],to[1 - axis],maximum[axis],from[axis],from[1 - axis]);
  }
  if(from.x < minimum.x || from.x > maximum.x || to.x < minimum.x || to.x > maximum.x) return;
  draw_line(image,vec2<int>{from},to,colour);
}

} // namespace tfx::presentation
