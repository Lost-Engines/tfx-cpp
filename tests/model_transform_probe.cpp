#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include "models/shape.h"
#include "render/integer_model_polygon.h"
#include "render/model_transform.h"

std::vector<uint8_t> model(std::array<vec3<int16_t>,3> const &vertices, uint16_t const scale) {
  std::vector<uint8_t> source(50);
  auto const store{[&](unsigned int const at,uint16_t const value) { source.at(at) = static_cast<uint8_t>(value >> 8);source.at(at + 1) = static_cast<uint8_t>(value); }};
  auto const emit{[&](std::initializer_list<uint16_t> const words) { for(auto const value : words) { source.push_back(static_cast<uint8_t>(value >> 8));source.push_back(static_cast<uint8_t>(value)); } }};
  store(0,32768);store(2,32767);store(34,14);store(48,65535);emit({48,scale});
  for(unsigned int i{0}; i != vertices.size(); ++i) emit({98,static_cast<uint16_t>(i),static_cast<uint16_t>(vertices[i].x),static_cast<uint16_t>(vertices[i].y),static_cast<uint16_t>(vertices[i].z)});
  emit({97,3,0,2,17,0,1,2,0,65535});
  return source;
}

int main(int const argc, char const *const argv[]) try {
  bool const pixels{argc == 2 && std::string_view{argv[1]} == "--pixels"};
  std::ifstream fixture;if(argc == 2 && !pixels) fixture.open(argv[1]);
  if(argc > 2 || (argc == 2 && !pixels && !fixture)) throw std::runtime_error{"expected [FILE] or --pixels"};
  auto &input{fixture.is_open() ? fixture : std::cin};
  bool wide;uint16_t scale;unsigned int draw_scale,cases{0};
  while(input >> wide >> scale >> draw_scale) {
    vec3<tfx::math::angle> angles;input >> angles.x >> angles.y >> angles.z;
    mat3<int32_t> matrix;for(auto &value : matrix.data) input >> value;
    vec3<int32_t> origin;input >> origin.x >> origin.y >> origin.z;
    std::array<vec3<int16_t>,3> vertices;for(auto &point : vertices) input >> point.x >> point.y >> point.z;
    auto view{tfx::render::original_camera({0,0,0},matrix,{160,100},wide ? tfx::render::aperture::missile_nose : tfx::render::aperture::normal)};
    view.far_distance = 100000;
    tfx::render::model_transform const transform{matrix,angles,tfx::render::scale_model_cache(origin,static_cast<uint8_t>(draw_scale))};
    auto const camera_vertices{[&](std::span<tfx::models::model_vertex const> const source) {
      std::vector<tfx::models::model_vertex> result;
      for(auto const &vertex : source) result.push_back({
        .position{transform.point(vertex.position,vertex.projection_scale)},
        .uv{0,0},
        .projection_scale{vertex.projection_scale},
      });
      return result;
    }};
    tfx::models::shape const shape{model(vertices,scale)};
    tfx::models::shape_context context;
    context.face_visibility = [&](std::span<tfx::models::model_vertex const> const source,tfx::models::facing_test const purpose) { return tfx::render::model_facing(camera_vertices(source),view,purpose); };
    auto const geometry{tfx::models::interpret(shape,context)};
    if(!geometry.warnings.empty()) throw std::runtime_error{"transformed model emitted warnings"};
    tfx::render::framebuffer output;output.pixels.fill(99);
    for(auto const &face : geometry.primitives) if(!tfx::render::integer_model_polygon(output,camera_vertices(face.vertices),view,17)) throw std::runtime_error{"unhandled transformed face"};
    uint64_t hash{14695981039346656037ull};for(auto const value : output.pixels) hash = (hash ^ value) * 1099511628211;
    if(pixels) std::cout.write(reinterpret_cast<char const*>(output.pixels.data()),output.pixels.size());
    else if(fixture.is_open()) {
      for(auto const value : transform.matrix().data) { int32_t expected;if(!(input >> expected) || value != expected) throw std::runtime_error{"native model basis mismatch"}; }
      uint64_t expected;if(!(input >> expected) || hash != expected) throw std::runtime_error{"native transformed model mismatch at " + std::to_string(cases)};
    } else { for(auto const value : transform.matrix().data) std::cout << value << ' ';std::cout << hash << '\n'; }
    ++cases;
  }
  return cases ? 0 : 1;
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
