#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include "resources/archive.h"

auto main(int const argc, char const *const argv[])->int try {
  std::filesystem::path data_directory{"."};
  for(int i{1}; i != argc; ++i) {
    std::string_view const option{argv[i]};
    if(option == "--help") {
      std::cout << "TFX C++ reconstruction\nUsage: tfx [--data-dir DIRECTORY]\nOriginal TFX game files are required. Reference: September 1994 CD, version 2.05." << std::endl;
      return EXIT_SUCCESS;
    }
    if(option == "--data-dir" && i + 1 < argc) data_directory = argv[++i];
    else if(option.starts_with("--data-dir=")) data_directory = option.substr(11);
    else throw std::runtime_error{"unrecognised or incomplete option: " + std::string{option}};
  }
  tfx::resources::archive const game{tfx::resources::find_game_archive(data_directory)};
  std::cout << "Loaded " << game.entries().size() << " TFX resources from " << data_directory << std::endl;
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
