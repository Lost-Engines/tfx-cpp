#include "integer_polygon.h"
#include <algorithm>
#include <bit>
#include <cstdlib>
#include <optional>
#include <vector>

namespace tfx::render {
namespace {
int16_t word(int32_t const value) { return math::signed_word(static_cast<uint16_t>(value)); }
int32_t wrap(uint32_t const value) { return std::bit_cast<int32_t>(value); }
using vertex_list = std::vector<vec2<int16_t>>;

vertex_list clip(vertex_list const &vertices, unsigned int const axis, int16_t const boundary, int const sign) {
  vertex_list result;
  for(unsigned int i{0}; i != vertices.size(); ++i) {
    auto const &a{vertices[i]}, &b{vertices[(i + 1) % vertices.size()]};
    int const da{word(a[axis] - boundary) * sign}, db{word(b[axis] - boundary) * sign};
    bool const inside{da >= 0};
    if(inside) result.emplace_back(a);
    if(inside == (db >= 0)) continue;
    int const aa{std::abs(da)}, ab{std::abs(db)};
    int const delta{word(b[1 - axis] - a[1 - axis])};
    // Native clippers calculate from the farther endpoint; equality chooses
    // the inside endpoint. This retains their directional IDIV rounding.
    int const other{aa > ab || (aa == ab && inside) ? a[1 - axis] + delta * aa / (aa + ab) : b[1 - axis] - delta * ab / (aa + ab)};
    vec2<int16_t> point;
    point[axis] = boundary;point[1 - axis] = word(other);result.emplace_back(point);
  }
  return result;
}
struct edge {
  unsigned int rows;
  int32_t position_q16;
  int32_t step_q16;
};
struct edge_chain {
  std::vector<edge> segments;
  int16_t final_x;
};
std::optional<edge_chain> chain(vertex_list const &vertices, unsigned int index, int const direction, int16_t const bottom) {
  edge_chain result;
  for(unsigned int count{0}; count <= vertices.size(); ++count) {
    auto const &a{vertices[index]};
    if(count && a.y >= bottom) { result.final_x = a.x;return result; }
    unsigned int const count_vertices{static_cast<unsigned int>(vertices.size())};
    index = (index + count_vertices + direction) % count_vertices;
    auto const &b{vertices[index]};
    int const height{b.y - a.y}, dx{b.x - a.x};
    if(height < 0) return std::nullopt;
    if(!height) continue;
    int const reciprocal{height == 1 ? 32767 : 32768 / height};
    int32_t const step{dx * 2 * reciprocal};
    int32_t const initial{wrap((static_cast<uint32_t>(a.x) << 16) + 32768u + (std::abs(dx) >= height ? static_cast<uint32_t>(step >> 1) : 0u))};
    result.segments.push_back({
      .rows{static_cast<unsigned int>(height)},
      .position_q16{initial},
      .step_q16{step},
    });
  }
  return std::nullopt;
}
class edge_walker {
private:
  edge_chain const &source;
  unsigned int index{0}, row{0};
  int32_t position{0};
public:
  explicit edge_walker(edge_chain const &chain) : source{chain} {
    if(!source.segments.empty()) position = source.segments.front().position_q16;
  }
  int x() const { return index == source.segments.size() ? source.final_x : position >> 16; }
  void advance() {
    if(index == source.segments.size()) return;
    if(++row == source.segments[index].rows) {
      ++index;row = 0;
      if(index != source.segments.size()) position = source.segments[index].position_q16;
    } else position = wrap(static_cast<uint32_t>(position) + static_cast<uint32_t>(source.segments[index].step_q16));
  }
};
}

void integer_polygon(framebuffer &output, std::span<vec2<int16_t> const> const input, uint8_t const colour, vec2<int16_t> const &minimum, vec2<int16_t> const &maximum) {
  if(input.size() < 3) return;
  vertex_list vertices;
  int x_low{32767},x_high{-32768},y_low{32767},y_high{-32768};
  for(auto const &v : input) {
    vertices.emplace_back(v);x_low = std::min(x_low,static_cast<int>(v.x));x_high = std::max(x_high,static_cast<int>(v.x));
    y_low = std::min(y_low,static_cast<int>(v.y));y_high = std::max(y_high,static_cast<int>(v.y));
  }
  if(x_high < minimum.x || x_low > maximum.x || y_high < minimum.y || y_low > maximum.y) return;
  int32_t const x1{word(vertices[1].x - vertices[0].x)}, x2{word(vertices[2].x - vertices[0].x)};
  int32_t const y1{word(vertices[1].y - vertices[0].y)}, y2{word(vertices[2].y - vertices[0].y)};
  if(wrap(static_cast<uint32_t>(x1 * y2) - static_cast<uint32_t>(x2 * y1)) < 0) return;
  // Native bounding-span overflow clamps all vertices before clipping.
  if(x_high - x_low > 32767 || y_high - y_low > 32767) for(auto &v : vertices) {
    v.x = std::clamp<int16_t>(v.x,-16383,16383);v.y = std::clamp<int16_t>(v.y,-16383,16383);
  }
  vertices = clip(vertices,1,maximum.y,-1);
  vertices = clip(vertices,1,minimum.y,1);
  vertices = clip(vertices,0,maximum.x,-1);
  vertices = clip(vertices,0,minimum.x,1);
  if(vertices.size() < 3) return;
  unsigned int top{0};int16_t bottom{vertices.front().y};
  for(unsigned int i{1}; i != vertices.size(); ++i) {
    if(vertices[i].y <= vertices[top].y) top = i;
    bottom = std::max(bottom,vertices[i].y);
  }
  auto const left{chain(vertices,top,-1,bottom)}, right{chain(vertices,top,1,bottom)};
  if(!left || !right) return;
  edge_walker l{*left},r{*right};
  for(int y{vertices[top].y}; y <= bottom; ++y) {
    int const first{std::max(0,l.x())},last{std::min(screen_width - 1,r.x())};
    if(y >= 0 && y < screen_height && first <= last) std::fill_n(output.pixels.begin() + y * screen_width + first,last - first + 1,colour);
    l.advance();r.advance();
  }
}

} // namespace tfx::render
