#include <cstdlib>
#include <iostream>
#include "planning/document.h"
#include "resources/archive.h"
#include "resources/compiled_panel.h"

int main(int const argc, char const *const argv[]) try {
  if(argc == 3 && std::string_view{argv[2]} == "--panel") {
    auto const panel{tfx::resources::decode_planner_panel(tfx::resources::read_file(std::filesystem::path{argv[1]} / "TFX.DAT"))};
    for(auto const *frame : {&panel.image,&panel.coverage}) std::cout.write(reinterpret_cast<char const*>(frame->pixels.data()),frame->pixels.size());
    return EXIT_SUCCESS;
  }
  if(argc == 3 && std::string_view{argv[2]} == "--palette") {
    auto const executable{tfx::resources::read_file(std::filesystem::path{argv[1]} / "TFX.DAT")};
    std::string hex;
    while(std::cin >> hex) {
      tfx::resources::bytes input;
      for(unsigned int at{0}; at < hex.size(); at += 2) input.push_back(static_cast<uint8_t>(std::stoul(hex.substr(at,2),nullptr,16)));
      auto const palette{tfx::resources::planner_palette(input,executable)};
      std::cout.write(reinterpret_cast<char const*>(palette.data()),palette.size());
    }
    return EXIT_SUCCESS;
  }
  if(argc != 2) throw std::runtime_error{"planning_probe DATA_DIRECTORY"};
  tfx::resources::archive const game{tfx::resources::find_game_archive(argv[1])};
  auto const string{[](std::string_view const text) {
    char constexpr digits[]{"0123456789abcdef"};
    for(uint8_t const byte : text) std::cout << digits[byte >> 4] << digits[byte & 15];
    std::cout << '|';
  }};
  uint32_t id;
  while(std::cin >> id) {
    auto const bytes{game.read(id)};
    try {
      tfx::planning::document const plan{std::string_view{reinterpret_cast<char const*>(bytes.data()),bytes.size()}};
      std::cout << plan.format << ' ';
      for(auto const word : plan.parameters.words()) std::cout << word << ' ';
      std::cout << '|';
      string(plan.map_images[0]);string(plan.world);string(plan.map_images[1]);string(plan.palette);string(plan.map_images[2]);
      std::cout << plan.routes.size() << '|';
      for(auto const &route : plan.routes) {
        string(route.name);
        for(auto const &point : route.points) std::cout << point.ordinal << ',' << point.cell.x << ',' << point.cell.y << ';';
        std::cout << '|';
      }
      string(plan.notes);
      std::cout << '\n';
    } catch(std::runtime_error const&) { std::cout << "invalid\n"; }
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
