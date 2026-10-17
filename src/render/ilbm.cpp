#include "ilbm.h"
#include <span>
#include <string_view>

namespace tfx::render {
namespace {

unsigned int constexpr planes{8}, plane_row_bytes{screen_width / planes};
unsigned int constexpr bitmap_header_bytes{20}, chunk_header_bytes{8}, form_header_bytes{12};
unsigned int constexpr palette_bytes{256 * 3};
unsigned int constexpr image_prefix_bytes{form_header_bytes + chunk_header_bytes + bitmap_header_bytes + chunk_header_bytes + palette_bytes + chunk_header_bytes};

auto pack_row(std::span<uint8_t const,plane_row_bytes> const row, std::vector<uint8_t> &output)->void {
  auto const start{output.size()};
  unsigned int position{0};
  while(position != row.size()) {
    unsigned int const begin{position++};
    if(position != row.size() && row[begin] == row[position]) {
      while(position != row.size() && row[position] == row[begin]) ++position;
      output.push_back(static_cast<uint8_t>(1 - static_cast<int>(position - begin)));
      output.push_back(row[begin]);
    } else {
      while(position != row.size() && (position + 1 == row.size() || row[position] != row[position + 1])) ++position;
      output.push_back(static_cast<uint8_t>(position - begin - 1));
      output.insert(output.end(),row.begin() + begin,row.begin() + position);
    }
  }
  // Native 0xdfc30 retains compression at exactly 40 bytes; a longer row
  // falls back to one literal packet containing the whole bitplane row.
  if(output.size() - start > row.size()) {
    output.resize(start);
    output.push_back(static_cast<uint8_t>(row.size() - 1));
    output.insert(output.end(),row.begin(),row.end());
  }
}

} // anonymous namespace

auto encode_ilbm(framebuffer const &image, dac_palette const &colours)->std::vector<uint8_t> {
  std::vector<uint8_t> body;
  body.reserve((plane_row_bytes + 1) * planes * screen_height);
  std::array<uint8_t,plane_row_bytes> row;
  for(unsigned int y{0}; y != screen_height; ++y) {
    for(unsigned int plane{0}; plane != planes; ++plane) {
      for(unsigned int x{0}; x != row.size(); ++x) {
        uint8_t bits{0};
        for(unsigned int bit{0}; bit != planes; ++bit) {
          unsigned int const pixel{image.pixels[y * screen_width + x * planes + bit]};
          bits |= static_cast<uint8_t>(((pixel >> plane) & 1u) << (planes - bit - 1));
        }
        row[x] = bits;
      }
      pack_row(row,body);
    }
  }
  std::vector<uint8_t> result;
  result.reserve(image_prefix_bytes + body.size());
  auto const word{[&](unsigned int const value, unsigned int const bytes) {
    for(unsigned int remaining{bytes}; remaining; --remaining) result.push_back(static_cast<uint8_t>(value >> ((remaining - 1) * 8)));
  }};
  auto const tag{[&](std::string_view const name) { result.insert(result.end(),name.begin(),name.end()); }};
  tag("FORM");word(image_prefix_bytes - chunk_header_bytes + static_cast<unsigned int>(body.size()),4);tag("ILBM");
  tag("BMHD");word(bitmap_header_bytes,4);
  word(screen_width,2);word(screen_height,2);word(0,2);word(0,2);
  word(planes,1);word(0,1);word(1,1);word(0,1);word(0,2);
  word(5,1);word(6,1);word(screen_width,2);word(screen_height,2);
  tag("CMAP");word(static_cast<unsigned int>(colours.size()),4);
  for(auto const value : colours) result.push_back(static_cast<uint8_t>((value & 63) << 2));
  tag("BODY");word(static_cast<unsigned int>(body.size()),4);
  result.insert(result.end(),body.begin(),body.end());
  // Original 0xdfe08 patches the exact body length, without an odd-byte pad.
  return result;
}

} // namespace tfx::render
