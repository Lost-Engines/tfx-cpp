#include "integer_model_polygon.h"
#include "integer_polygon.h"
#include <cmath>
#include <limits>
#include <vector>

namespace tfx::render {

bool integer_model_polygon(framebuffer &output, std::span<models::model_vertex const> const vertices, camera const &view, uint8_t const colour) {
  if(view.projection != projection_mode::original_model || vertices.size() < 3) return false;
  int constexpr near_depth{16}, maximum_depth{32767};
  std::vector<vec2<int16_t>> projected;
  projected.reserve(vertices.size());
  for(auto const &vertex : vertices) {
    if(vertex.projection_scale <= 0 || vertex.position.z > view.far_distance) return false;
    double const depth{std::floor(std::nearbyint(vertex.position.z / vertex.projection_scale * 65536) / 65536)};
    // Native B9434 marks signed-word depths <=16 as unprojected. Their later
    // camera-space clipping needs a separate path, not invented screen points.
    if(!(depth > near_depth) || depth > maximum_depth) return false;
    auto const point{view.project(vertex.position,vertex.projection_scale)};
    if(!std::isfinite(point.x) || !std::isfinite(point.y) || point.x < std::numeric_limits<int16_t>::min() || point.x > std::numeric_limits<int16_t>::max() || point.y < std::numeric_limits<int16_t>::min() || point.y > std::numeric_limits<int16_t>::max()) return false;
    projected.emplace_back(static_cast<int16_t>(point.x),static_cast<int16_t>(point.y));
  }
  // Do screen clipping after integer projection, as the original does. A
  // floating 3D side-plane intersection changes the clipped endpoint rounding.
  integer_polygon(output,projected,colour,view.viewport_minimum,view.viewport_maximum);
  return true;
}

} // namespace tfx::render
