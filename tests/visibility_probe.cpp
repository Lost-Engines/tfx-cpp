#include <fstream>
#include <iostream>
#include <stdexcept>
#include "render/point_projection.h"

int main(int const argc, char const *const argv[]) try {
  std::ifstream fixture;
  if(argc == 2) fixture.open(argv[1]);
  if(argc > 2 || (argc == 2 && !fixture)) throw std::runtime_error{"expected [FILE]"};
  auto &input{argc == 2 ? fixture : std::cin};
  unsigned int cases{0};int16_t radius;
  while(input >> radius) {
    tfx::render::point_projection projection;
    vec3<int32_t> point;
    for(auto &value : projection.matrix.data) input >> value;
    input >> projection.position_q16.x >> projection.position_q16.y >> projection.position_q16.z >> point.x >> point.y >> point.z >> projection.origin.x >> projection.origin.y >> projection.maximum.x >> projection.maximum.y;
    if(!input) throw std::runtime_error{"incomplete visibility input"};
    bool const visible{projection.sphere_visible(point,radius)};
    if(argc == 2) {
      bool expected;
      if(!(input >> expected) || visible != expected) throw std::runtime_error{"native sphere visibility differs at case " + std::to_string(cases)};
    } else std::cout << visible << '\n';
    ++cases;
  }
  return cases ? 0 : 1;
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
