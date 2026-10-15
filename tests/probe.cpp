#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string_view>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif // _WIN32
#include "resources/archive.h"

namespace {

void word(uint32_t const value) {
  for(unsigned int shift{0}; shift != 32; shift += 8) std::cout.put(static_cast<char>(value >> shift));
}

} // anonymous namespace

auto main(int const argc, char const *const argv[])->int try {
  if(argc != 3 || std::string_view{argv[1]} != "archive") throw std::runtime_error{"usage: tfx_probe archive DATA_DIRECTORY"};
#ifdef _WIN32
  _setmode(_fileno(stdout), _O_BINARY);
#endif // _WIN32
  tfx::resources::archive const game{tfx::resources::find_game_archive(argv[2])};
  word(static_cast<uint32_t>(game.entries().size()));
  for(auto const &entry : game.entries()) {
    auto const decoded{game.read(entry.id)};
    word(entry.id);
    word(static_cast<uint32_t>(decoded.size()));
    std::cout.write(reinterpret_cast<char const*>(decoded.data()), static_cast<std::streamsize>(decoded.size()));
  }
  if(!std::cout) throw std::runtime_error{"resource probe output failed"};
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
