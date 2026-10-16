#include "sprites.h"
#include <algorithm>

namespace tfx::render {

void draw_sprite(framebuffer &target, resources::indexed_image const &image, vec2<int> const &centre, framebuffer *const coverage) {
  // Native 0xc0ef8 supplies a sprite centre; palette index zero is transparent.
  int const left{centre.x - static_cast<int>(image.size.x / 2)};
  int const top{centre.y - static_cast<int>(image.size.y / 2)};
  // Right overflow clips in four-pixel VGA groups, preserving the starting plane phase.
  int const width{static_cast<int>(image.size.x)};
  int const clipped_right{left >= 0 && left + width >= screen_width - 1
    ? (left / 4 + width / 4 - (left + width - (screen_width - 1)) / 4) * 4
    : left + width};
  for(int y{std::max(0,top)}; y < std::min(screen_height,top + static_cast<int>(image.size.y)); ++y) {
    for(int x{std::max(0,left)}; x < std::min(screen_width,clipped_right); ++x) {
      auto const pixel{image.pixels.at(static_cast<unsigned int>(y - top) * image.size.x + static_cast<unsigned int>(x - left))};
      if(!pixel) continue;
      auto const destination{static_cast<unsigned int>(y * screen_width + x)};
      target.pixels[destination] = pixel;
      if(coverage) coverage->pixels[destination] = 255;
    }
  }
}
void draw_monochrome(framebuffer &target, resources::monochrome_image const &image, vec2<int> const &position, uint8_t const colour, framebuffer *const coverage) {
  // Native 0xcda48 uses a top-left origin and MSB-first packed rows. A set bit may paint black.
  unsigned int const stride{(image.size.x + 7) / 8};
  for(int y{std::max(0,position.y)}; y < std::min(screen_height,position.y + static_cast<int>(image.size.y)); ++y) {
    for(int x{std::max(0,position.x)}; x < std::min(screen_width,position.x + static_cast<int>(image.size.x)); ++x) {
      unsigned int const column{static_cast<unsigned int>(x - position.x)}, row{static_cast<unsigned int>(y - position.y)};
      if(!(image.rows.at(row * stride + column / 8) & (128u >> (column % 8)))) continue;
      auto const destination{static_cast<unsigned int>(y * screen_width + x)};
      target.pixels[destination] = colour;
      if(coverage) coverage->pixels[destination] = 255;
    }
  }
}

} // namespace tfx::render
