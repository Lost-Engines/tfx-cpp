#include "rounded_model_polygon.h"
#include "render/integer_model_polygon.h"
#include "render/integer_polygon.h"
#include "render/pattern_raster.h"
#include "render/software_renderer.h"
#include <bit>
#include <cmath>
#include <limits>

namespace tfx::render {

bool rounded_model_polygon(framebuffer &output, std::span<models::model_vertex const> const vertices, camera const &view, uint8_t const colour, int const mode, uint16_t &seed) {
  if(view.projection != projection_mode::original_model || vertices.size() != 4) return false;
  std::array<vec3<int32_t>,4> camera;
  for(unsigned int i{0}; i != camera.size(); ++i) {
    if(vertices[i].projection_scale <= 0) return false;
    for(unsigned int axis{0}; axis != 3; ++axis) {
      double const value{std::nearbyint(vertices[i].position[axis] / vertices[i].projection_scale * 65536)};
      if(!std::isfinite(value) || value < std::numeric_limits<int32_t>::min() || value > std::numeric_limits<int32_t>::max()) return false;
      camera[i][axis] = static_cast<int32_t>(value);
    }
    // This original consumer omits a whole rounded face when a corner is near;
    // it does not send it through the ordinary polygon near-plane clipper.
    if(camera[i].z >> 16 <= 16) return true;
  }
  auto const corners{project_model_face(vertices,view)};
  if(!corners || corners->size() != 4) return false;
  if(auto const facing{model_facing(vertices,view,models::facing_test::polygon)}; facing && !*facing) return true;
  std::array<vec2<int16_t>,4> midpoints;
  for(unsigned int i{0}; i != 4; ++i) {
    vec3<int32_t> sum;
    for(unsigned int axis{0}; axis != 3; ++axis) sum[axis] = std::bit_cast<int32_t>(static_cast<uint32_t>(camera[i][axis]) + static_cast<uint32_t>(camera[(i + 1) % 4][axis]));
    int32_t const depth{sum.z >> 16};
    if(!depth) return false; // The original dword IDIV does not complete.
    for(unsigned int axis{0}; axis != 2; ++axis) {
      // BC89F retains its normal-aperture shift even in missile-nose view;
      // unlike B9434, its two immediates are not patched by the wide setter.
      unsigned int constexpr midpoint_projection_shift{8};
      int32_t const coordinate{(sum[axis] >> midpoint_projection_shift) / depth};
      midpoints[i][axis] = math::signed_word(static_cast<uint16_t>(coordinate + static_cast<int32_t>(view.projection_origin[axis])));
    }
  }
  pattern_polygon(output,seed,integer_polygon_spans(midpoints,view.viewport_minimum,view.viewport_maximum),colour,mode);
  for(unsigned int i{0}; i != 4; ++i) {
    auto const curve{rounded_corner(vec2<int32_t>{midpoints[(i + 3) % 4]},vec2<int32_t>{(*corners)[i]},vec2<int32_t>{midpoints[i]})};
    std::array<vec2<int16_t>,8> points;
    for(unsigned int j{0}; j != points.size(); ++j) points[j] = vec2<int16_t>{curve[j]};
    // BC78E temporarily bypasses BD68C's winding test for each corner fan.
    pattern_polygon(output,seed,integer_polygon_spans(points,view.viewport_minimum,view.viewport_maximum,polygon_facing::unchecked),colour,mode);
  }
  return true;
}

} // namespace tfx::render
