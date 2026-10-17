#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include "render/integer_model_polygon.h"

std::vector<uint8_t> program(std::array<vec3<int16_t>,3> const &vertices, uint16_t const scale) {
  std::vector<uint8_t> source(50);
  auto const store{[&](unsigned int const at,uint16_t const value) { source.at(at) = static_cast<uint8_t>(value >> 8);source.at(at + 1) = static_cast<uint8_t>(value); }};
  auto const emit{[&](std::initializer_list<uint16_t> const words) { for(auto const value : words) { source.push_back(static_cast<uint8_t>(value >> 8));source.push_back(static_cast<uint8_t>(value)); } }};
  store(2,32767);store(18,0);store(34,14);store(48,65535);
  emit({48,scale});
  for(unsigned int i{0}; i != vertices.size(); ++i) emit({98,static_cast<uint16_t>(i),static_cast<uint16_t>(vertices[i].x),static_cast<uint16_t>(vertices[i].y),static_cast<uint16_t>(vertices[i].z)});
  emit({97,3,0,21,0,1,2,0});
  auto const field{static_cast<unsigned int>(source.size() - 2)};
  emit({2,17,0,1,2,2,17,0,1,2,0}); // Two draws on the untaken branch.
  store(field,static_cast<uint16_t>(source.size() - field));
  emit({2,19,0,1,2,0,65535}); // One draw on the taken branch.
  return source;
}

int main(int const argc, char const *const argv[]) try {
  bool const pixels{argc == 2 && std::string_view{argv[1]} == "--pixels"};
  std::ifstream fixture;if(argc == 2 && !pixels) fixture.open(argv[1]);
  if(argc > 2 || (argc == 2 && !pixels && !fixture)) throw std::runtime_error{"expected [FILE | --pixels]"};
  auto &input{fixture.is_open() ? fixture : std::cin};
  bool wide;uint16_t scale;vec3<int16_t> offset;unsigned int cases{0};
  mat3<int32_t> const identity{32767,0,0,0,32767,0,0,0,32767};
  while(input >> wide >> scale >> offset.x >> offset.y >> offset.z) {
    std::array<vec3<int16_t>,3> vertices;
    for(auto &point : vertices) input >> point.x >> point.y >> point.z;
    tfx::models::shape const shape{program(vertices,scale)};
    auto view{tfx::render::original_camera({0,0,0},identity,{160,100},wide ? tfx::render::aperture::missile_nose : tfx::render::aperture::normal)};
    view.far_distance = 100000;
    auto const transform{[&](std::span<tfx::models::model_vertex const> const source) {
      std::vector<tfx::models::model_vertex> result;
      for(auto const &point : source) result.push_back({
        .position{view.transform(point.position + vec3d{offset})},
        .uv{0,0},
        .projection_scale{point.projection_scale},
      });
      return result;
    }};
    tfx::models::shape_context context;
    context.face_visibility = [&](std::span<tfx::models::model_vertex const> const points,tfx::models::facing_test const purpose) { return tfx::render::model_facing(transform(points),view,purpose); };
    auto const geometry{tfx::models::interpret(shape,context)};
    if(!geometry.warnings.empty()) throw std::runtime_error{"synthetic model emitted a warning"};
    tfx::render::framebuffer output;output.pixels.fill(99);
    for(auto const &face : geometry.primitives) if(!tfx::render::integer_model_polygon(output,transform(face.vertices),view,static_cast<uint8_t>(face.colour))) throw std::runtime_error{"unhandled synthetic model face"};
    uint64_t hash{14695981039346656037ull};for(auto const value : output.pixels) hash = (hash ^ value) * 1099511628211;
    if(pixels) std::cout.write(reinterpret_cast<char const*>(output.pixels.data()),output.pixels.size());
    else if(fixture.is_open()) { uint64_t draws,expected;if(!(input >> draws >> expected) || draws != geometry.steps - 7 || expected != hash) throw std::runtime_error{"native model program mismatch at case " + std::to_string(cases)}; }
    else std::cout << geometry.steps - 7 << ' ' << hash << '\n';
    ++cases;
  }
  return cases ? 0 : 1;
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
