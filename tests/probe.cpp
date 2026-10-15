#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <utility>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif // _WIN32
#include "math/native.h"
#include "models/shape.h"
#include "resources/archive.h"
#include "world/definition.h"
#include "world/environment.h"

namespace {

void word(uint32_t const value) {
  for(unsigned int shift{0}; shift != 32; shift += 8) std::cout.put(static_cast<char>(value >> shift));
}

} // anonymous namespace

auto main(int const argc, char const *const argv[])->int try {
  if(argc < 2) throw std::runtime_error{"usage: tfx_probe archive|shape DATA_DIRECTORY, or sine|rotation|conditions|random"};
  std::string_view const mode{argv[1]};
  std::cout << std::setprecision(17);
  if(mode == "sine") {
    for(auto const value : tfx::math::sine_table()) std::cout << value << ' ';
    std::cout << std::endl;
  } else if(mode == "rotation") {
    unsigned int x{0}, y{0}, z{0};
    while(std::cin >> x >> y >> z) {
      auto const matrix{tfx::math::rotation_words(vec3<tfx::math::angle>{static_cast<uint16_t>(x), static_cast<uint16_t>(y), static_cast<uint16_t>(z)})};
      for(auto const value : matrix.data) std::cout << value << ' ';
      std::cout << '\n';
    }
  } else if(mode == "conditions") {
    unsigned int opcode{0}, operand{0}, state{0};
    while(std::cin >> opcode >> operand >> state) std::cout << tfx::models::condition(static_cast<uint16_t>(opcode), static_cast<uint16_t>(operand), static_cast<uint8_t>(state), tfx::math::signed_word(static_cast<uint16_t>(state)), static_cast<uint16_t>(state)) << '\n';
  } else if(mode == "random") {
    tfx::math::random_state state;
    unsigned int count{0};
    while(std::cin >> count) {
      if(!count) throw std::runtime_error{"zero variant count in probe"};
      auto const value{state.next()};
      std::cout << value % count << ' ' << state.low << ' ' << state.high << '\n';
    }
  } else {
    if(argc != 3) throw std::runtime_error{"resource probe needs a data directory"};
    tfx::resources::archive const game{tfx::resources::find_game_archive(argv[2])};
    if(mode == "archive") {
#ifdef _WIN32
      _setmode(_fileno(stdout), _O_BINARY);
#endif // _WIN32
      word(static_cast<uint32_t>(game.entries().size()));
      for(auto const &entry : game.entries()) {
        auto const decoded{game.read(entry.id)};
        word(entry.id);
        word(static_cast<uint32_t>(decoded.size()));
        std::cout.write(reinterpret_cast<char const*>(decoded.data()), static_cast<std::streamsize>(decoded.size()));
      }
    } else if(mode == "definitions") {
      auto const names{tfx::world::model_names(game.read("ss/ssinfo.fn"))};
      uint32_t id{0};
      while(std::cin >> id) {
        tfx::world::definition const definition{game.read(id), names};
        std::cout << '[' << definition.flags << ",[";
        bool first{true};
        for(unsigned int slot{0}; slot != definition.parts.size(); ++slot) {
          auto const &part{definition.parts[slot]};
          if(part.name.empty()) continue;
          if(!std::exchange(first, false)) std::cout << ',';
          std::cout << '[' << slot << ',' << std::quoted(part.name) << ',' << part.rotation.x << ',' << part.rotation.y << ',' << part.rotation.z << ']';
        }
        std::cout << "],[";
        first = true;
        for(auto const &draw : definition.draws) {
          if(!std::exchange(first, false)) std::cout << ',';
          std::cout << '[' << draw.slot << ',' << draw.anchor.x << ',' << draw.anchor.y << ',' << draw.anchor.z << ']';
        }
        std::cout << "],[";
        first = true;
        for(auto const &stream : definition.streams) {
          if(!std::exchange(first, false)) std::cout << ',';
          std::cout << '[' << stream.part << ',' << stream.parameter << ",[";
          bool first_word{true};
          for(auto const value : stream.words) {
            if(!std::exchange(first_word, false)) std::cout << ',';
            std::cout << value;
          }
          std::cout << "]]";
        }
        std::cout << "]]\n";
      }
    } else if(mode == "environment") {
      std::string name;
      while(std::cin >> name) {
        tfx::world::environment const environment{game, name};
        std::cout << '[' << environment.status << ',' << std::quoted(environment.palette_name) << ",[";
        bool first{true};
        for(unsigned int z{0}; z != tfx::world::map_height; ++z) {
          for(unsigned int x{0}; x != tfx::world::map_width; ++x) {
            if(!std::exchange(first, false)) std::cout << ',';
            std::cout << '[' << environment.tile_id(x,z) << ',' << std::quoted(environment.variant(x,z)) << ']';
          }
        }
        std::cout << "]]\n";
      }
    } else if(mode == "shape") {
      uint32_t id{0};
      unsigned int status{0}, state{0}, level{0};
      while(std::cin >> id >> status >> state >> level) {
        tfx::models::shape const program{game.read(id)};
        tfx::models::shape_context context;
        context.status = static_cast<uint16_t>(status);
        context.parameters[7] = static_cast<uint8_t>(state);
        context.level = level;
        context.facing = false;
        auto const geometry{tfx::models::interpret(program, context)};
        std::cout << '[' << geometry.steps << ",[";
        bool first{true};
        for(auto const &p : geometry.primitives) {
          if(!std::exchange(first, false)) std::cout << ',';
          std::cout << '[' << std::to_underlying(p.kind) << ',' << p.colour << ',' << p.mode << ',' << p.pixel_size << ',' << p.radius << ',' << p.source_address << ",[";
          bool first_vertex{true};
          for(auto const &v : p.vertices) {
            if(!std::exchange(first_vertex, false)) std::cout << ',';
            std::cout << '[' << v.position.x << ',' << v.position.y << ',' << v.position.z << ',' << v.shade << ',' << v.uv.x << ',' << v.uv.y << ']';
          }
          std::cout << "]]";
        }
        std::cout << "]]\n";
      }
    } else throw std::runtime_error{"unknown probe mode"};
  }
  if(!std::cout) throw std::runtime_error{"probe output failed"};
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
