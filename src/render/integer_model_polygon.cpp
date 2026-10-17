#include "integer_model_polygon.h"
#include "integer_polygon.h"
#include "near_clip.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <optional>
#include <ranges>
#include <vector>

namespace tfx::render {
namespace {
int16_t word(int32_t const value) { return math::signed_word(static_cast<uint16_t>(value)); }
int32_t wrap(uint32_t const value) { return std::bit_cast<int32_t>(value); }
using camera_vertices = std::vector<vec3<int32_t>>;
using screen_vertices = std::vector<vec2<int16_t>>;

std::optional<camera_vertices> native_points(std::span<models::model_vertex const> const vertices, camera const &view) {
  if(view.projection != projection_mode::original_model || vertices.size() < 3) return std::nullopt;
  camera_vertices result;result.reserve(vertices.size());
  for(auto const &vertex : vertices) {
    if(vertex.projection_scale <= 0) return std::nullopt;
    vec3<int32_t> point;
    for(unsigned int axis{0}; axis != 3; ++axis) {
      double const fixed{std::nearbyint(vertex.position[axis] / vertex.projection_scale * 65536)};
      if(!std::isfinite(fixed) || fixed < std::numeric_limits<int32_t>::min() || fixed > std::numeric_limits<int32_t>::max()) return std::nullopt;
      point[axis] = static_cast<int32_t>(fixed);
    }
    result.emplace_back(point);
  }
  return result;
}
std::optional<vec2<int16_t>> project(vec3<int32_t> const &point, camera const &view) {
  int32_t const depth{point.z >> 16};
  if(depth <= model_near_depth) return std::nullopt;
  unsigned int const shift{projection_shift(view.opening)};
  vec2<int32_t> const quotient{(point.x >> shift) / depth,(point.y >> shift) / depth};
  // Native IDIV uses a word destination. Leave its overflow domain to the
  // host's separate fallback; valid quotients add the origin with WORD wrap.
  if(quotient.x < std::numeric_limits<int16_t>::min() || quotient.x > std::numeric_limits<int16_t>::max() || quotient.y < std::numeric_limits<int16_t>::min() || quotient.y > std::numeric_limits<int16_t>::max()) return std::nullopt;
  return vec2<int16_t>{word(quotient.x + static_cast<int32_t>(view.projection_origin.x)),word(quotient.y + static_cast<int32_t>(view.projection_origin.y))};
}
std::optional<screen_vertices> clip(camera_vertices const &vertices, camera const &view) {
  screen_vertices result;result.reserve(vertices.size() + 2);
  vec2<int16_t> const origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)};
  for(unsigned int i{0}; i != vertices.size(); ++i) {
    auto const &a{vertices[i]}, &b{vertices[(i + 1) % vertices.size()]};
    bool const inside_a{a.z >> 16 > model_near_depth}, inside_b{b.z >> 16 > model_near_depth};
    if(inside_a) {
      auto const screen{project(a,view)};
      if(!screen) return std::nullopt;
      result.emplace_back(*screen);
    }
    if(inside_a != inside_b) result.emplace_back(project_near_plane(inside_a ? intersect_near_plane(b,a) : intersect_near_plane(a,b),view.opening,origin));
  }
  return result;
}
bool winding(screen_vertices const &vertices, models::facing_test const purpose) {
  if(vertices.size() < 3) return false;
  auto const difference{[&](int32_t const value) { return purpose == models::facing_test::polygon ? static_cast<int32_t>(word(value)) : value; }};
  vec2<int32_t> const a{difference(vertices[1].x - vertices[0].x),difference(vertices[1].y - vertices[0].y)};
  vec2<int32_t> const b{difference(vertices[2].x - vertices[0].x),difference(vertices[2].y - vertices[0].y)};
  return wrap(static_cast<uint32_t>(a.x) * static_cast<uint32_t>(b.y) - static_cast<uint32_t>(a.y) * static_cast<uint32_t>(b.x)) >= 0;
}
bool plane_facing(camera_vertices const &vertices) {
  // Native BB890 uses signed high words, WORD edge differences, a wrapped
  // cross product and shared right shifts until all normal axes fit a word.
  vec3<int16_t> a,b,c;
  for(unsigned int axis{0}; axis != 3; ++axis) {
    a[axis] = word(vertices[0][axis] >> 16);b[axis] = word(vertices[1][axis] >> 16);c[axis] = word(vertices[2][axis] >> 16);
  }
  vec3<int32_t> u,v;
  for(unsigned int axis{0}; axis != 3; ++axis) { u[axis] = word(b[axis] - a[axis]);v[axis] = word(c[axis] - a[axis]); }
  vec3<uint32_t> const cross{vec3<uint32_t>{u}.cross(vec3<uint32_t>{v})};
  vec3<int32_t> normal{wrap(cross.x),wrap(cross.y),wrap(cross.z)};
  int32_t constexpr minimum_axis{std::numeric_limits<int16_t>::min()},maximum_axis{std::numeric_limits<int16_t>::max()};
  while(normal.x < minimum_axis || normal.x > maximum_axis || normal.y < minimum_axis || normal.y > maximum_axis || normal.z < minimum_axis || normal.z > maximum_axis) {
    normal.x >>= 1;normal.y >>= 1;normal.z >>= 1;
  }
  // The dot product uses the negated SECOND vertex, with word NEG wrapping.
  uint32_t dot{0};
  for(unsigned int axis{0}; axis != 3; ++axis) dot += static_cast<uint32_t>(word(-static_cast<int32_t>(b[axis]))) * static_cast<uint32_t>(normal[axis]);
  return wrap(dot) < 0;
}
}

bool integer_model_polygon(framebuffer &output, std::span<models::model_vertex const> const vertices, camera const &view, uint8_t const colour, colour_map const *const remap) {
  if(std::ranges::any_of(vertices,[&](auto const &vertex) { return vertex.position.z > view.far_distance; })) return false;
  auto const native{native_points(vertices,view)};
  if(!native) return false;
  bool const shaded{std::ranges::all_of(vertices,[](auto const &vertex) { return vertex.shade >= 0; })};
  if(shaded) {
    std::vector<uint16_t> shades;shades.reserve(vertices.size());
    for(auto const &vertex : vertices) {
      double const shade{vertex.shade * 256};
      if(!std::isfinite(shade) || shade < 0 || shade > std::numeric_limits<uint16_t>::max()) return false;
      shades.push_back(static_cast<uint16_t>(shade));
    }
    std::vector<indexed_vertex> projected;projected.reserve(vertices.size() + 2);
    vec2<int16_t> const origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)};
    for(unsigned int i{0}; i != vertices.size(); ++i) {
      unsigned int const next{(i + 1) % static_cast<unsigned int>(vertices.size())};
      auto const &a{(*native)[i]}, &b{(*native)[next]};
      bool const inside_a{a.z >> 16 > model_near_depth}, inside_b{b.z >> 16 > model_near_depth};
      if(inside_a) {
        auto const point{project(a,view)};
        if(!point) return false;
        projected.push_back({
          .position{vec2<int16_t>{*point}},
          .shade_q8{shades[i]},
        });
      }
      if(inside_a == inside_b) continue;
      auto const intersection{inside_a ? intersect_shaded_near_plane(b,a,shades[next],shades[i]) : intersect_shaded_near_plane(a,b,shades[i],shades[next])};
      projected.push_back({
        .position{project_near_plane(intersection.position,view.opening,origin)},
        .shade_q8{intersection.shade_q8},
      });
    }
    static colour_maps const identity;
    integer_gouraud_polygon(output,projected,remap ? *remap : identity.row(0),view.viewport_minimum,view.viewport_maximum);
    return true;
  }
  if(std::ranges::any_of(vertices,[](auto const &vertex) { return vertex.shade >= 0; })) return false;
  auto const screen{clip(*native,view)};
  if(!screen) return false;
  if(screen->size() >= 3) integer_polygon(output,*screen,colour,view.viewport_minimum,view.viewport_maximum);
  return true;
}

std::optional<bool> model_facing(std::span<models::model_vertex const> const vertices, camera const &view, models::facing_test const purpose) {
  auto const native{native_points(vertices,view)};
  if(!native) return std::nullopt;
  if(purpose == models::facing_test::branch) {
    if(std::ranges::any_of(*native | std::views::take(3),[](auto const &point) { return point.z >> 16 <= model_near_depth; })) return plane_facing(*native);
    screen_vertices screen;
    for(unsigned int i{0}; i != 3; ++i) {
      auto const point{project((*native)[i],view)};
      if(!point) return std::nullopt;
      screen.emplace_back(*point);
    }
    // BB842 subtracts sign-extended screen words in full dwords, unlike the
    // raster's independent WORD differences. Its multiply/subtract still wraps.
    return winding(screen,models::facing_test::branch);
  }
  auto const screen{clip(*native,view)};
  return screen ? std::optional<bool>{winding(*screen,models::facing_test::polygon)} : std::nullopt;
}

} // namespace tfx::render
