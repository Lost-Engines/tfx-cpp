#include <bit>
#include <iostream>
#include <string_view>
#include "flight/aerodynamic_step.h"
#include "aerodynamic_snapshot.h"
#include "weapons/definition.h"

int main(int const argc, char const *const argv[]) try {
  bool const trace{argc == 3 && std::string_view{argv[2]} == "--trace"};
  if(argc != 2 && !trace) throw std::runtime_error{"expected TFX.DAT [--trace]"};
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
    auto state{tfx::flight::initialise_aerodynamic_flight(frames.at(craft - 1),stores,initial,wind[0],damage,random)};
    for(auto const value : aerodynamic_snapshot(state,damage,random)) std::cout << value << ' ';
    std::cout << '\n';
    if(trace) {
      unsigned int count; std::cin >> count;
      for(unsigned int tick{0}; tick != count; ++tick) {
        uint64_t seconds; unsigned int source,up,left,down,right,alt,accelerate,decelerate,wind_enabled,warp,pressure,braking,crashing,wet,gear_damage,surface;
        int joystick_x,joystick_y,mouse_x,mouse_y;
        if(!(std::cin >> seconds >> source >> up >> left >> down >> right >> alt >> accelerate >> decelerate >> joystick_x >> joystick_y >> mouse_x >> mouse_y >> wind_enabled >> warp >> pressure >> braking >> crashing >> wet >> gear_damage >> surface)) throw std::runtime_error{"truncated aerodynamic trace input"};
        tfx::flight::aerodynamic_tick_context const step{
          .input{
            .source{static_cast<tfx::flight::control_source>(source)},
            .keys{
              .up{up != 0},
              .left{left != 0},
              .down{down != 0},
              .right{right != 0},
            },
            .joystick{static_cast<int16_t>(joystick_x),static_cast<int16_t>(joystick_y)},
            .mouse{static_cast<int16_t>(mouse_x),static_cast<int16_t>(mouse_y)},
            .alt{alt != 0},
            .accelerate{accelerate != 0},
            .decelerate{decelerate != 0},
          },
          .seconds{std::bit_cast<double>(seconds)},
          .ground_elevation_steps{static_cast<int16_t>(height)},
          .surface_celsius{initial.surface_celsius},
          .terrain_present{terrain != 0},
          .rough_surface{surface == 2},
          .carrier_surface{surface == 3},
          .wheel_brakes{braking != 0},
          .gear_damage_enabled{gear_damage != 0},
          .precipitation{wet != 0},
          .time_warp{warp != 0},
          .crashing{crashing != 0},
          .stick_pressure{pressure != 0},
          .wind_enabled{wind_enabled != 0},
          .terrain_wind_boost{terrain_boost != 0},
          .weather_wind_boost{boost != 0},
        };
        auto const events{tfx::flight::advance_aerodynamic_flight(state,damage,random,wind[0],step)};
        for(auto const value : aerodynamic_snapshot(state,damage,random)) std::cout << value << ' ';
        std::cout << events.ground.gear_impacts << ' ' << events.ground.cockpit_bump << ' ' << events.afterburner.size() << ' ';
        for(auto const change : events.afterburner) std::cout << std::to_underlying(change) << ' ';
        std::cout << '\n';
      }
    }
  }
  return 0;
} catch(std::exception const &error) { std::cerr << error.what() << '\n'; return 1; }
