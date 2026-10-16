#include "cursor.h"
#include <algorithm>
#include <stdexcept>

namespace tfx::presentation {
std::array<pointer_style,2> load_pointers(std::span<uint8_t const> const executable) {
  resources::binary_view const view{executable};
  unsigned int constexpr data{973476}, idle_table{0xdf08}, active_table{0xdf30}, record_bytes{20};
  auto const shape{[&](unsigned int const record) {
    unsigned int const pointer{data + view.le32(record)};
    if(view.byte(pointer) != 1) throw std::runtime_error{"unexpected native menu pointer frame count"};
    unsigned int const frame{view.le16(pointer + 1)};
    unsigned int const pixels{view.byte(pointer + frame) * 2u * view.byte(pointer + frame + 1)};
    auto decoded{resources::decode_sprites(view.slice(pointer,frame + 2 + pixels))};
    return pointer_shape{
      .image{std::move(decoded.front())},
      .adjustment{view.signed_le16(record + 8),view.signed_le16(record + 10)},
    };
  }};
  std::array<pointer_style,2> result;
  for(unsigned int index{0}; index != result.size(); ++index) result[index] = {
    .idle{shape(data + idle_table + index * record_bytes)},
    .active{shape(data + active_table + index * record_bytes)},
  };
  return result;
}
void draw_pointer(render::framebuffer &target, pointer_shape const &shape, vec2<int16_t> const &position) {
  // Native 0xd20d8 supplies the adjusted sprite centre to 0xc0ef8; index zero is transparent here.
  int const left{position.x + shape.adjustment.x - static_cast<int>(shape.image.size.x / 2)};
  int const top{position.y + shape.adjustment.y - static_cast<int>(shape.image.size.y / 2)};
  // The original clips right overflow in four-pixel VGA groups, retaining the starting plane phase.
  int const width{static_cast<int>(shape.image.size.x)};
  int const clipped_right{left >= 0 && left + width >= render::screen_width - 1
    ? (left / 4 + width / 4 - (left + width - (render::screen_width - 1)) / 4) * 4
    : left + width};
  for(int y{std::max(0,top)}; y < std::min(render::screen_height,top + static_cast<int>(shape.image.size.y)); ++y) {
    for(int x{std::max(0,left)}; x < std::min(render::screen_width,clipped_right); ++x) {
      auto const pixel{shape.image.pixels.at(static_cast<unsigned int>(y - top) * shape.image.size.x + static_cast<unsigned int>(x - left))};
      if(pixel) target.pixels[static_cast<unsigned int>(y * render::screen_width + x)] = pixel;
    }
  }
}
} // namespace tfx::presentation
