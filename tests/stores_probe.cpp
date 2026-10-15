#include <bit>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include "flight/stores.h"

auto main()->int try {
  unsigned int aircraft{0};
  while(std::cin >> aircraft) {
    tfx::flight::airframe_load airframe;
    airframe.aircraft = static_cast<tfx::flight::player_aircraft>(aircraft);
    std::cin >> airframe.moment_a >> airframe.moment_b >> airframe.fuel_capacity;
    tfx::flight::loadout stores;
    for(auto &store : stores) {
      int mass{0};
      unsigned int drag{0}, tank{0}, occupied{0};
      if(!(std::cin >> store.position.x >> store.position.y >> store.position.z >> mass >> drag >> tank >> occupied)) throw std::runtime_error{"truncated loadout replay"};
      store.properties.mass_kg = static_cast<int16_t>(mass);
      store.properties.drag = std::bit_cast<float>(drag);
      store.properties.fuel_tank = tank != 0;
      store.occupied = occupied != 0;
    }
    auto const result{tfx::flight::accumulate_stores(airframe,stores)};
    for(auto const value : {result.drag,result.mass_kg,result.moment_a,result.moment_b,result.total_moment_a,result.total_moment_b,result.fuel_capacity}) std::cout << std::bit_cast<uint64_t>(value) << ' ';
    std::cout << result.fuel_tank << '\n';
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
