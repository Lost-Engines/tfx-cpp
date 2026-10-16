#include "executable_tables.h"
#include <stdexcept>
#include <algorithm>

namespace tfx::resources {

executable_tables::executable_tables(std::filesystem::path const &path) {
  /// Read original circle spans as data; no original instructions execute at runtime
  auto const source{read_file(path)};
  uint64_t checksum{14695981039346656037ull};
  for(auto const byte : source) checksum = (checksum ^ byte) * 1099511628211ull;
  if(source.size() != 1032503 || checksum != 0xcc1e305ba7e177f0ull) throw std::runtime_error{"this reconstruction currently requires the September 1994 TFX 2.05 executable (TFX.DAT)"};
  weapons = weapons::load_definitions(source);
  pointers = presentation::load_pointers(source);
  pilot_assets = std::make_unique<presentation::pilot_assets>(source);
  font_data = std::make_unique<presentation::fonts>(source);
  binary_view const view{source};
  unsigned int constexpr circle_base{0x70aa4 + 0x65a84}, circle_limit_field{0x70aa4 + 0x66ea0};
  auto const limit{view.le16(circle_limit_field)};
  circles.resize(limit);
  unsigned int constexpr data_file{973476}, mapping{data_file + 0x7a44}, advances{data_file + 0x7a84}, glyph_file{0xf5350};
  std::ranges::copy(view.slice(data_file + 0xd55c,text_palette.size()),text_palette.begin());
  for(unsigned int index{0}; index != 512; ++index) {
    auto const character{view.byte(data_file + 0xa8 + index)};
    if(!character) break;
    timer_expired_message.push_back(static_cast<char>(character));
    if(index == 511) throw std::runtime_error{"unterminated native timer message"};
  }
  for(unsigned int index{0}; index != 64; ++index) {
    auto const type{view.signed_le16(data_file + 0x884c + index * 2)};
    if(type == -1) break;
    ship_target_types.push_back(type);
    if(index == 63) throw std::runtime_error{"unterminated native ship target list"};
  }
  auto const anchor{[&](unsigned int const address) { return vec3<int16_t>{view.signed_le16(data_file + address),view.signed_le16(data_file + address + 2),view.signed_le16(data_file + address + 4)}; }};
  unsigned int constexpr empty_record{data_file + 0x809c + weapons::empty_pylon * 48};
  arming.empty_role = static_cast<weapons::weapon_role>(view.byte(empty_record + 20));
  arming.empty_category = view.byte(empty_record + 29);
  std::array<unsigned int,3> constexpr default_bases{0x7dd0,0x7ec0,0x7e48}, default_counts{12,6,12};
  for(unsigned int aircraft{0}; aircraft != arming.defaults.size(); ++aircraft) {
    arming.defaults[aircraft].resize(default_counts[aircraft]);
    for(unsigned int fit{0}; fit != default_counts[aircraft]; ++fit) for(unsigned int pair{0}; pair != weapons::pylon_pairs; ++pair) arming.defaults[aircraft][fit][pair] = view.signed_le16(data_file + default_bases[aircraft] + (fit * weapons::pylon_pairs + pair) * 2);
  }
  for(unsigned int index{0}; index != arming.next.size(); ++index) arming.next[index] = view.le16(data_file + 0x869c + index * 2);
  for(unsigned int index{0}; index != cannon_mounts.size(); ++index) cannon_mounts[index] = anchor(0x8690 + index * 6);
  std::array<unsigned int,3> constexpr aircraft_mounts{0x8654,0x8618,0x85dc};
  for(unsigned int aircraft{0}; aircraft != store_mounts.size(); ++aircraft) for(unsigned int slot{0}; slot != store_mounts[aircraft].size(); ++slot) store_mounts[aircraft][slot] = anchor(aircraft_mounts[aircraft] + slot * 6);
  for(unsigned int i{0}; i != aircraft_envelopes.size(); ++i) aircraft_envelopes[i] = view.byte(data_file + 0x93b4 + i);
  for(unsigned int i{0}; i != formations.size(); ++i) {
    auto const at{data_file + 0x5984 + i * 14};
    formations[i] = {
      .heading{view.le16(at)},
      .distance{std::bit_cast<int32_t>(view.le32(at + 6))},
      .height{std::bit_cast<int32_t>(view.le32(at + 10))},
      .forward_distance{std::bit_cast<int32_t>(view.le32(at + 2))},
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

presentation::fonts const &executable_tables::presentation_fonts() const { return *font_data; }

presentation::pilot_assets const &executable_tables::pilots() const {
  return *pilot_assets;
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
