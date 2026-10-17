#include "integer_model_polygon.h"
#include "integer_polygon.h"
#include "near_clip.h"
#include <cmath>
#include <limits>
#include <optional>
#include <vector>

namespace tfx::render {

bool integer_model_polygon(framebuffer &output, std::span<models::model_vertex const> const vertices, camera const &view, uint8_t const colour) {
  if(view.projection != projection_mode::original_model || vertices.size() < 3) return false;
  struct native_vertex {
    vec3<int32_t> camera;
    std::optional<vec2<int16_t>> screen;
  };
  std::vector<native_vertex> native;
  native.reserve(vertices.size());
  for(auto const &vertex : vertices) {
    if(vertex.projection_scale <= 0 || vertex.position.z > view.far_distance) return false;
    vec3<int32_t> camera;
    for(unsigned int axis{0}; axis != 3; ++axis) {
      double const fixed{std::nearbyint(vertex.position[axis] / vertex.projection_scale * 65536)};
      if(!std::isfinite(fixed) || fixed < std::numeric_limits<int32_t>::min() || fixed > std::numeric_limits<int32_t>::max()) return false;
      camera[axis] = static_cast<int32_t>(fixed);
    }
    native_vertex point{
      .camera{vec3<int32_t>{camera}},
      .screen{},
    };
    // Native B9434 marks signed-word depths <=16 as unprojected. D7998
    // subsequently clips their edges using the retained raw camera positions.
    if(camera.z >> 16 > model_near_depth) {
      auto const screen{view.project(vertex.position,vertex.projection_scale)};
      if(!std::isfinite(screen.x) || !std::isfinite(screen.y) || screen.x < std::numeric_limits<int16_t>::min() || screen.x > std::numeric_limits<int16_t>::max() || screen.y < std::numeric_limits<int16_t>::min() || screen.y > std::numeric_limits<int16_t>::max()) return false;
      point.screen.emplace(static_cast<int16_t>(screen.x),static_cast<int16_t>(screen.y));
    }
    native.push_back(std::move(point));
  }
  std::vector<vec2<int16_t>> projected;
  projected.reserve(native.size() + 2);
  vec2<int16_t> const origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)};
  for(unsigned int i{0}; i != native.size(); ++i) {
    auto const &a{native[i]}, &b{native[(i + 1) % native.size()]};
    if(a.screen) projected.emplace_back(*a.screen);
    if(a.screen.has_value() != b.screen.has_value()) {
      auto const crossing{a.screen ? intersect_near_plane(b.camera,a.camera) : intersect_near_plane(a.camera,b.camera)};
      projected.emplace_back(project_near_plane(crossing,view.opening,origin));
    }
  }
  // Screen clipping follows integer projection. Floating side-plane
  // intersections would change the native endpoint rounding at the viewport.
  if(projected.size() >= 3) integer_polygon(output,projected,colour,view.viewport_minimum,view.viewport_maximum);
  return true;
}

} // namespace tfx::render
