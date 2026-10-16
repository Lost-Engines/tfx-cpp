#include <cstdlib>
#include <iostream>
#include <map>
#include "render/sprites.h"
#include "resources/archive.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"usage: sprite_probe DATA_DIRECTORY"};
  auto const archive{tfx::resources::find_game_archive(argv[1])};
  tfx::resources::archive const game{archive};
  auto const executable{tfx::resources::read_file(archive.parent_path() / "TFX.DAT")};
  tfx::resources::binary_view const source{executable};
  std::map<std::string,std::vector<tfx::resources::indexed_image>> banks;
  char kind{0};
  while(std::cin >> kind) {
    tfx::render::framebuffer image, coverage;
    image.pixels.fill(99);
    if(kind == 'S') {
      std::string name;unsigned int frame{0};vec2<int> centre;
      std::cin >> name >> frame >> centre.x >> centre.y;
      if(!banks.contains(name)) banks.emplace(name,tfx::resources::decode_sprites(game.read(name)));
      tfx::render::draw_sprite(image,banks.at(name).at(frame),centre,&coverage);
    } else if(kind == 'B') {
      unsigned int field{0}, colour{0};vec2<int> position;
      std::cin >> field >> position.x >> position.y >> colour;
      unsigned int const width{source.byte(field)}, height{source.byte(field + 1)};
      auto const bitmap{tfx::resources::decode_monochrome(source.slice(field,2 + ((width + 7) / 8) * height))};
      tfx::render::draw_monochrome(image,bitmap,position,static_cast<uint8_t>(colour),&coverage);
    } else throw std::runtime_error{"unknown image probe command"};
    std::cout.write(reinterpret_cast<char const*>(image.pixels.data()),image.pixels.size());
    std::cout.write(reinterpret_cast<char const*>(coverage.pixels.data()),coverage.pixels.size());
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
