#include "math/floating_environment.h"
#include "airframes.h"
#include <cmath>
#include <optional>
#include <stdexcept>

namespace tfx::flight {
namespace {

class preset_literals {
private:
  resources::binary_view const &source;
  unsigned int begin;
  unsigned int end;

public:
  preset_literals(resources::binary_view const &source, unsigned int const begin, unsigned int const end) : source{source}, begin{begin}, end{end} {
    source.slice(begin,end - begin);
  }
  double number(unsigned int const field) const {
    // Read the two literal words assigned to a compiled double. This recognises
    // only MOV [absolute address], immediate data; no original code executes.
    std::array<std::optional<uint32_t>,2> words;
    for(unsigned int at{begin}; at + 10 <= end; ++at) {
      if(source.le16(at) != 0x05c7) continue;
      auto const address{source.le32(at + 2)};
      if(address != field && address != field + 4) continue;
      auto &word{words[(address - field) / 4]};
      if(word) throw std::runtime_error{"ambiguous aircraft preset literal"};
      word = source.le32(at + 6);
    }
    if(!words[0] || !words[1]) throw std::runtime_error{"missing aircraft preset literal"};
    return std::bit_cast<double>(static_cast<uint64_t>(*words[0]) | (static_cast<uint64_t>(*words[1]) << 32));
  }
};

double constant(resources::binary_view const &source, unsigned int const field) {
  unsigned int constexpr data{973476};
  return std::bit_cast<double>(static_cast<uint64_t>(source.le32(data + field)) | (static_cast<uint64_t>(source.le32(data + field + 4)) << 32));
}
long double root_argument(resources::binary_view const &source, unsigned int const low, unsigned int const high) {
  if(source.byte(low) != 0x68 || source.byte(high) != 0x68) throw std::runtime_error{"missing aircraft moment argument"};
  auto const argument{std::bit_cast<double>(static_cast<uint64_t>(source.le32(low + 1)) | (static_cast<uint64_t>(source.le32(high + 1)) << 32))};
  return std::sqrt(static_cast<long double>(argument));
}

} // anonymous namespace

std::array<airframe,3> load_airframes(std::span<uint8_t const> const executable) {
  math::floating_environment const environment;
  resources::binary_view const source{executable};
  std::array<airframe,3> result;
  std::array<unsigned int,3> constexpr starts{0x98234,0x97598,0x96918}, ends{0x98eba,0x98231,0x97598};
  std::array<unsigned int,3> constexpr coordinates{0x13bd0,0x13c20,0x13c70};
  for(unsigned int aircraft{0}; aircraft != result.size(); ++aircraft) {
    preset_literals const literals{source,starts[aircraft],ends[aircraft]};
    auto &profile{result[aircraft]};
    profile.stores.aircraft = static_cast<player_aircraft>(aircraft + 1);
    profile.stores.fuel_capacity = literals.number(0x14850);
    for(unsigned int slot{0}; slot != store_slots; ++slot) for(unsigned int axis{0}; axis != coordinates.size(); ++axis) profile.mounts[slot][axis] = literals.number(coordinates[axis] + slot * 8u);
    if(aircraft == 0) {
      // Native 0x953a4 is sqrt, followed by these ordered extended-precision multiplications.
      profile.stores.moment_a = static_cast<double>(root_argument(source,0x985bc,0x985a3) * constant(source,0x28f8) * constant(source,0x2900) * constant(source,0x2908));
      profile.stores.moment_b = static_cast<double>(root_argument(source,0x985f7,0x985f2) * constant(source,0x2910));
    } else if(aircraft == 1) {
      profile.stores.moment_a = static_cast<double>(root_argument(source,0x9798c,0x97973) * constant(source,0x2848));
      profile.stores.moment_b = static_cast<double>(root_argument(source,0x979bb,0x979b6) * constant(source,0x2850));
    } else {
      profile.stores.moment_a = literals.number(0x142c8);
      profile.stores.moment_b = literals.number(0x14258);
    }
  }
  return result;
}

} // namespace tfx::flight
