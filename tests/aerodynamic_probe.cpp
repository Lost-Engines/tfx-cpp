#include <bit>
#include <iostream>
#include "aerodynamic_snapshot.h"
#include "weapons/definition.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"expected TFX.DAT"};
  auto const source{tfx::resources::read_file(argv[1])};
  auto const frames{tfx::flight::load_aerodynamic_airframes(source)};
  auto const wind{tfx::flight::load_aerodynamic_wind_parameters(source)};
  auto const weapons{tfx::weapons::load_definitions(source)};
  unsigned int craft,model,landed,cold,terrain,boost,terrain_boost,gear,slot,weapon,occupied,low,high;
  int height,fixed_speed;
  while(std::cin >> craft >> model >> landed >> cold >> terrain >> boost >> terrain_boost >> gear >> slot >> weapon >> occupied >> low >> high >> height >> fixed_speed) {
    tfx::flight::aerodynamic_start_context context{
      .fixed_speed{fixed_speed},
      .ground_elevation_steps{static_cast<int16_t>(height)},
      .landed{landed != 0},
      .cold_start{cold != 0},
      .terrain_present{terrain != 0},
    };
    for(auto &value : context.position) {
      uint32_t bits; std::cin >> bits;
      value = std::bit_cast<float>(bits);
    }
    for(unsigned int row{0}; row != 3; ++row) std::cin >> context.orientation.right[row] >> context.orientation.down[row] >> context.orientation.forward[row];
    unsigned int temperature; int celsius;
    std::cin >> temperature >> celsius;
    context.heading = context.orientation.angles().y;
    tfx::flight::damage_state damage;
    damage.systems[std::to_underlying(tfx::flight::aircraft_system::landing_gear)] = static_cast<tfx::flight::system_condition>(gear);
    tfx::math::random_state random{
      .low{static_cast<uint16_t>(low)},
      .high{static_cast<uint16_t>(high)},
    };
    tfx::flight::loadout stores;
    if(occupied) {
      auto const &definition{weapons.at(weapon)};
      stores.at(slot) = {
        .position{vec3d{frames.at(craft - 1).stores_and_mounts.mounts.at(slot)}},
        .properties{
          .mass_kg{definition.mass},
          .drag{definition.drag},
          .fuel_tank{definition.role == tfx::weapons::weapon_role::external_tank},
        },
        .occupied{true},
      };
    }
    tfx::flight::aerodynamic_wind_context const wind_context{
      .terrain_wind_boost{terrain_boost != 0},
      .weather_wind_boost{boost != 0},
    };
    tfx::flight::aerodynamic_initial_context const initial{
      .placement{context},
      .model{model ? tfx::flight::aerodynamic_model::realistic : tfx::flight::aerodynamic_model::military_spec},
      .wind{wind_context},
      .surface_celsius{temperature ? std::optional<int16_t>{static_cast<int16_t>(celsius)} : std::nullopt},
    };
    auto const state{tfx::flight::initialise_aerodynamic_flight(frames.at(craft - 1),stores,initial,wind[0],damage,random)};
    for(auto const value : aerodynamic_snapshot(state,damage,random)) std::cout << value << ' ';
    std::cout << '\n';
  }
  return 0;
} catch(std::exception const &error) { std::cerr << error.what() << '\n'; return 1; }
