#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include "render/integer_model_polygon.h"

int main(int const argc, char const *const argv[]) try {
  bool pixels{false},shaded{false};std::ifstream fixture;
  for(int i{1}; i != argc; ++i) {
    std::string_view const option{argv[i]};
    if(option == "--pixels") pixels = true;
    else if(option == "--shaded") shaded = true;
    else { if(fixture.is_open()) throw std::runtime_error{"expected [FILE] [--pixels] [--shaded]"};fixture.open(argv[i]);if(!fixture) throw std::runtime_error{"cannot open polygon fixture"}; }
  }
  auto &input{fixture.is_open() ? fixture : std::cin};
  unsigned int cases{0},count;bool wide;double scale;
  mat3<int32_t> const identity{32767,0,0,0,32767,0,0,0,32767};
  while(input >> wide >> count >> scale) {
    auto view{tfx::render::original_camera({0,0,0},identity,{160,100},wide ? tfx::render::aperture::missile_nose : tfx::render::aperture::normal)};
    view.far_distance = 100000; // Far-range eligibility is separate from the native near-clip capture.
    input >> view.viewport_minimum.x >> view.viewport_minimum.y >> view.viewport_maximum.x >> view.viewport_maximum.y;
    std::vector<tfx::models::model_vertex> vertices;
    for(unsigned int i{0}; i != count; ++i) {
      vec3<int32_t> point;input >> point.x >> point.y >> point.z;
      vertices.push_back({
        .position{vec3d{point} / 65536 * scale},
        .uv{0,0},
        .shade{shaded ? static_cast<double>(192 + i % 16) : -1},
        .projection_scale{scale},
      });
    }
    tfx::render::framebuffer output;output.pixels.fill(99);
    if(!tfx::render::integer_model_polygon(output,vertices,view,17)) throw std::runtime_error{"unhandled world polygon at case " + std::to_string(cases)};
    uint64_t hash{14695981039346656037ull};
    for(auto const value : output.pixels) hash = (hash ^ value) * 1099511628211;
    if(pixels) std::cout.write(reinterpret_cast<char const*>(output.pixels.data()),output.pixels.size());
    else if(fixture.is_open()) { uint64_t expected;if(!(input >> expected) || expected != hash) throw std::runtime_error{"native flat model polygon mismatch at case " + std::to_string(cases)}; }
    else std::cout << hash << '\n';
    ++cases;
  }
  return cases ? 0 : 1;
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
