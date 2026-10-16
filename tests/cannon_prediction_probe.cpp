#include <cstdlib>
#include <iostream>
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "weapons/cannon_prediction.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"usage: cannon_prediction_probe DATA_DIRECTORY"};
  auto const archive{tfx::resources::find_game_archive(argv[1])};
  tfx::resources::executable_tables const tables{archive.parent_path() / "TFX.DAT"};
  vec3<int32_t> anchor{0,0,0};vec3<tfx::math::angle> angles{0,0,0};int32_t speed{0};vec2<int32_t> bounds{0,0};
  while(std::cin >> anchor.x >> anchor.y >> anchor.z >> angles.x >> angles.y >> angles.z >> speed >> bounds.x >> bounds.y) {
    auto const points{tfx::weapons::predict_cannon(tables.weapons[0],anchor,angles,speed,bounds)};
    for(auto const &point : points) std::cout << point.x << ' ' << point.y << ' ' << point.z << ' ';
    std::cout << '\n';
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
