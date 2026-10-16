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
}

} // namespace tfx::cockpit
