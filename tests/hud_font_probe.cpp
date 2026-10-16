#include <cstdlib>
#include <iostream>
#include "render/software_renderer.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"hud_font_probe TFX_DAT"};
  tfx::resources::executable_tables const tables{argv[1]};
  tfx::render::software_renderer renderer{tables};
  int x{0}, y{0};unsigned int colour{0};std::string hex;
  while(std::cin >> x >> y >> colour >> hex) {
    std::string text;
    if(hex != "-") for(unsigned int at{0}; at < hex.size(); at += 2) text += static_cast<char>(std::stoul(hex.substr(at,2),nullptr,16));
    renderer.output.pixels.fill(55);
    renderer.text(x,y,text,static_cast<uint8_t>(colour));
    auto const &pixels{renderer.output.pixels};
    std::cout.write(reinterpret_cast<char const*>(pixels.data()),pixels.size());
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
