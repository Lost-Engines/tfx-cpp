#include "executable_tables.h"
#include <stdexcept>

namespace tfx::resources {

executable_tables::executable_tables(std::filesystem::path const &path) {
  /// Read original circle spans as data; no original instructions execute at runtime
  auto const source{read_file(path)};
  uint64_t checksum{14695981039346656037ull};
  for(auto const byte : source) checksum = (checksum ^ byte) * 1099511628211ull;
  if(source.size() != 1032503 || checksum != 0xcc1e305ba7e177f0ull) throw std::runtime_error{"this reconstruction currently requires the September 1994 TFX 2.05 executable (TFX.DAT)"};
  binary_view const view{source};
  unsigned int constexpr circle_base{0x70aa4 + 0x65a84}, circle_limit_field{0x70aa4 + 0x66ea0};
  auto const limit{view.le16(circle_limit_field)};
  circles.resize(limit);
  unsigned int constexpr data_file{973476}, mapping{data_file + 0x7a44}, advances{data_file + 0x7a84}, glyph_file{0xf5350};
  for(unsigned int i{0}; i != aircraft_envelopes.size(); ++i) aircraft_envelopes[i] = view.byte(data_file + 0x93b4 + i);
  for(unsigned int i{0}; i != formations.size(); ++i) {
    auto const at{data_file + 0x5984 + i * 14};
    formations[i] = {
      .heading{view.le16(at)},
      .distance{std::bit_cast<int32_t>(view.le32(at + 6))},
      .height{std::bit_cast<int32_t>(view.le32(at + 10))},
    };
  }
  for(unsigned int i{0}; i != character_map.size(); ++i) character_map[i] = view.byte(mapping + i);
  for(unsigned int i{0}; i != glyphs.size(); ++i) {
    auto const at{glyph_file + i * 8};
    if(view.byte(at) != 8 || view.byte(at + 1) != 6) throw std::runtime_error{"unexpected native HUD glyph dimensions"};
    glyphs[i].advance = view.byte(advances + i) + 1;
    for(unsigned int row{0}; row != 6; ++row) glyphs[i].rows[row] = view.byte(at + 2 + row);
  }
  for(unsigned int radius{1}; radius != limit; ++radius) {
    auto const spans{view.slice(circle_base + view.le16(circle_base + (radius - 1) * 2), radius)};
    circles[radius].assign(spans.begin(), spans.end());
  }
}

std::span<uint8_t const> executable_tables::circle(unsigned int const radius) const {
  /// The native constructor rejects zero and radii at or beyond its table limit
  if(radius >= circles.size()) return {};
  return circles[radius];
}

hud_glyph const *executable_tables::glyph(unsigned char const character) const {
  auto const index{character_map[character & 63]};
  return index < glyphs.size() ? &glyphs[index] : nullptr;
}

} // namespace tfx::resources
