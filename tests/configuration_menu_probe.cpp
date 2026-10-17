#include <bit>
#include <utility>
#include <iostream>
#include "presentation/configuration_menu.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"menu probe requires original executable"};
  auto const executable{tfx::resources::read_file(argv[1])};
  tfx::presentation::configuration_menu_assets const assets{executable};
  tfx::presentation::widget_font const font{executable};
  unsigned int model,source,detail,scale,green,g,precipitation,crashing,gear,wind,temperature,recovery,page,action;
  while(std::cin >> model >> source >> detail >> scale >> green >> g >> precipitation >> crashing >> gear >> wind >> temperature >> recovery >> page >> action) {
    tfx::configuration::settings state;
    state.model = static_cast<tfx::simulation::flight_model>(model);
    state.preferred_control = state.control = static_cast<tfx::flight::control_source>(source);
    state.detail = static_cast<uint8_t>(detail);
    state.joystick_scale = std::bit_cast<float>(scale);
    state.hud_green = static_cast<uint16_t>(green);
    state.effects = {
      .g_force{static_cast<tfx::configuration::g_effects>(g)},
      .precipitation{static_cast<uint8_t>(precipitation)},
      .crashing{static_cast<uint8_t>(crashing)},
      .gear_damage{static_cast<uint8_t>(gear)},
      .wind{static_cast<uint8_t>(wind)},
      .temperature{static_cast<uint8_t>(temperature)},
      .recovery{static_cast<uint8_t>(recovery)},
    };
    tfx::presentation::configuration_menu menu{state,assets,font};
    if(page == 1) menu.select(static_cast<unsigned int>(menu.widgets().size() - 1));
    else if(page == 2) menu.select(static_cast<unsigned int>(menu.widgets().size() - 3));
    auto const result{menu.select(action)};
    std::cout << std::to_underlying(state.model) + 0u << ' ' << std::to_underlying(state.control) + 0u << ' ' << static_cast<unsigned int>(state.detail) << ' ' << std::bit_cast<uint32_t>(state.joystick_scale) << ' ';
    for(unsigned int const value : {std::to_underlying(state.effects.g_force),state.effects.precipitation,state.effects.crashing,state.effects.gear_damage,state.effects.wind,state.effects.temperature,state.effects.recovery}) std::cout << value << ' ';
    std::cout << static_cast<unsigned int>(menu.page()) << ' ' << static_cast<unsigned int>(result) << '\n';
    tfx::render::framebuffer image;
    menu.draw(image);
    std::cout.write(reinterpret_cast<char const*>(image.pixels.data()),image.pixels.size());
  }
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
