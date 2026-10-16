#include "math/floating_environment.h"
#include "stores.h"
#include <limits>
#include <stdexcept>

namespace tfx::flight {

store_effects accumulate_stores(airframe_load const &airframe, loadout const &stores) {
  math::floating_environment const environment;
  /// Native 0x95dc8 rounds each accumulated field to double, retaining extended intermediates within each contribution
  using calculation = long double;
  if constexpr(std::numeric_limits<calculation>::digits != 64) throw std::runtime_error{"native flight calculations currently require an x87-precision arithmetic backend"};
  double constexpr external_tank_multiplier{2};
  store_effects result;
  for(auto const &store : stores) {
    if(!store.occupied) continue;
    auto const &definition{store.properties};
    vec3<calculation> const offset{store.position};
    vec2<calculation> const plane_a{offset.x,offset.y}, plane_b{offset.x,offset.z};
    result.drag = static_cast<double>(static_cast<calculation>(definition.drag) + result.drag);
    result.moment_a = static_cast<double>(plane_a.length_sq() * definition.mass_kg + result.moment_a);
    result.moment_b = static_cast<double>(plane_b.length_sq() * definition.mass_kg + result.moment_b);
    result.mass_kg = static_cast<double>(static_cast<calculation>(definition.mass_kg) + result.mass_kg);
    result.fuel_tank = result.fuel_tank || definition.fuel_tank;
  }
  result.total_moment_a = static_cast<double>(static_cast<calculation>(airframe.moment_a) + result.moment_a);
  result.total_moment_b = static_cast<double>(static_cast<calculation>(airframe.moment_b) + result.moment_b);
  result.fuel_capacity = airframe.fuel_capacity;
  if(airframe.aircraft == player_aircraft::eurofighter && result.fuel_tank) result.fuel_capacity *= external_tank_multiplier;
  return result;
}

} // namespace tfx::flight
