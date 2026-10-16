#include <charconv>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <type_traits>
#include "air_snapshot.h"
#include "actors/air.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"

int main(int const argc, char const *const argv[]) try {
  if(argc < 2 || argc > 3) throw std::runtime_error{"air_probe DATA_DIRECTORY [--verbose]"};
  bool const verbose{argc == 3 && std::string_view{argv[2]} == "--verbose"};
  auto const path{tfx::resources::find_game_archive(argv[1])};
  tfx::resources::archive const game{path};
  tfx::resources::executable_tables const tables{path.parent_path() / "TFX.DAT"};
  auto const profiles{tfx::actors::profiles(game.read("waybin/craftype.cfg"))};
  std::string name;
  unsigned int ticks{0},intact{0};
  while(std::cin >> name >> ticks >> intact) {
    uint32_t identifier{0};
    auto const [end,error]{std::from_chars(name.data(),name.data() + name.size(),identifier,16)};
    auto const bytes{error == std::errc{} && end == name.data() + name.size() ? game.read(identifier) : game.read(name)};
    tfx::actors::program const program{bytes};
    auto const initial{tfx::actors::initialise(program,profiles,tables.formations)};
    tfx::actors::air_runtime state{program,initial,profiles,tables.formations,tables.aircraft_envelopes};
    tfx::actors::air_context const context{
      .intact_ground_target{[intact](vec2<int16_t> const&) { return intact != 0; }},
    };
    for(unsigned int tick{0}; tick != ticks; ++tick) {
      auto const requests{state.advance(context)};
      auto const digest{tfx::test::air_snapshot(program,state,requests,verbose ? &std::cout : nullptr)};
      if(!verbose) std::cout << digest;
      std::cout << '\n';
    }
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
