#include "instrument_assets.h"
#include <algorithm>
#include <stdexcept>

namespace tfx::cockpit {

instrument_assets::instrument_assets(std::span<uint8_t const> const executable) {
  resources::binary_view const source{executable};
  unsigned int constexpr data{973476};
  auto const string{[&](unsigned int const address) {
    std::string result;
    for(unsigned int index{0}; index != 128; ++index) {
      auto const byte{source.byte(data + address + index)};
      if(!byte) return result;
      result.push_back(static_cast<char>(byte));
    }
    throw std::runtime_error{"unterminated original instrument string"};
  }};
  auto const real{[&](unsigned int const address) {
    return std::bit_cast<double>(static_cast<uint64_t>(source.le32(data + address)) | (static_cast<uint64_t>(source.le32(data + address + 4)) << 32));
  }};
  for(unsigned int index{0}; index != character_map.size(); ++index) character_map[index] = source.byte(data + 0x7688 + index);
  font_bank = string(0x166c);
  std::ranges::replace(font_bank,'\\','/');
  if(font_bank.starts_with('/')) font_bank.erase(0,1);
  unsigned_clock_formats = {string(0x17e4),string(0x17ec)};
  signed_clock_formats = {string(0x17f0),string(0x17f8)};
  fuel_format = string(0x17fc);
  critical_fuel = real(0x1803);
  low_fuel = real(0x180b);
  throttle_formats = {string(0x181c),string(0x1818),string(0x1814)};
  throttle_percent = std::bit_cast<float>(source.le32(data + 0x1821));
  ecm_label = string(0x1828);
  stealth_label = string(0x182c);
  decoy_formats = {string(0x1838),string(0x1834)};
  display_bank = string(0x1694);
  std::ranges::replace(display_bank,'\\','/');
  if(display_bank.starts_with('/')) display_bank.erase(0,1);
  for(unsigned int index{0}; index != display_origins.size(); ++index) display_origins[index] = {source.signed_le16(data + 0x7c98 + index * 8),source.signed_le16(data + 0x7c9a + index * 8)};
  std::array<unsigned int,9> constexpr bitmap_fields{0x7b84,0x7b8c,0x7b93,0x7b9a,0x7ba1,0x7ba9,0x7bb1,0x7bb7,0x7bcc};
  for(unsigned int index{0}; index != masks.size(); ++index) {
    auto const at{data + bitmap_fields[index]};
    unsigned int const size{2u + ((source.byte(at) + 7u) / 8u) * source.byte(at + 1)};
    masks[index] = resources::decode_monochrome(source.slice(at,size));
  }
  for(unsigned int plane{0}; plane != store_order.size(); ++plane) for(unsigned int slot{0}; slot != store_order[plane].size(); ++slot) {
    store_order[plane][slot] = source.byte(data + 0x7be1 + plane * 10 + slot);
    store_positions[plane][slot] = {source.signed_le16(data + 0x7c00 + plane * 40 + slot * 4),source.signed_le16(data + 0x7c02 + plane * 40 + slot * 4)};
  }
  for(unsigned int index{0}; index != system_positions.size(); ++index) {
    system_positions[index] = {source.signed_le16(data + 0x7cb0 + index * 4),source.signed_le16(data + 0x7cb2 + index * 4)};
    auto const at{data + 0x7d10 + index * 8};
    system_boxes[index] = {{
      {source.signed_le16(at),source.signed_le16(at + 2)},
      {source.signed_le16(at + 4),source.signed_le16(at + 6)},
    }};
    system_labels[index] = string(source.le32(data + 0x7ce0 + index * 4));
  }
  for(unsigned int index{0}; index != fuel_cells.size(); ++index) {
    auto const at{data + 0x7c78 + index * 8};
    fuel_cells[index] = {{
      {source.signed_le16(at),source.signed_le16(at + 2)},
      {source.signed_le16(at + 4),source.signed_le16(at + 6)},
    }};
  }
  flight_formats = {string(0x1b80),string(0x1b88),string(0x1b8c)};
  zero_range = string(0x1b90);
  engine_formats = {string(0x1bb4),string(0x1bc0)};
  fuel_total_format = string(0x1bd4);
  speed_scale = std::bit_cast<float>(source.le32(data + 0x57a8));
  altitude_scale = std::bit_cast<float>(source.le32(data + 0x1b92));
  gauge_fuel_scale = real(0x1ba6);
  gauge_throttle_scale = std::bit_cast<float>(source.le32(data + 0x1bae));
  engine_percent = real(0x1bcb);
}

} // namespace tfx::cockpit
