#include "arming_preview.h"
#include <algorithm>
#include <utility>
#include "render/integer_model_polygon.h"
#include "render/model_transform.h"
#include "render/model_metrics.h"
#include "world/model_placement.h"
#include "world/model_orientation.h"

namespace tfx::presentation {
namespace {

vec2<int16_t> constexpr viewport_minimum{10,10}, viewport_maximum{200,180};
vec2d constexpr projection_origin{105,75};
vec3d constexpr aircraft_position{0,1,160};
int32_t constexpr aircraft_distance{1200};

template<typename Draw> void clipped(render::software_renderer &renderer, Draw const &draw) {
  auto const previous{renderer.output};
  draw();
  for(int y{0}; y != render::screen_height; ++y) for(int x{0}; x != render::screen_width; ++x) {
    if(x >= viewport_minimum.x && x <= viewport_maximum.x && y >= viewport_minimum.y && y <= viewport_maximum.y) continue;
    unsigned int const offset{static_cast<unsigned int>(y * render::screen_width + x)};
    renderer.output.pixels[offset] = previous.pixels[offset];
  }
}
render::camera aircraft_view(arming_state const &state) {
  bool const overview{state.mode == arming_mode::overview};
  auto view{render::orbit_camera({overview ? math::angle{0x2fff} : state.angles.x,overview ? math::angle{0x7fff} : state.angles.y,0},aircraft_distance,projection_origin)};
  view.viewport_minimum = vec2<int16_t>{viewport_minimum};
  view.viewport_maximum = vec2<int16_t>{viewport_maximum};
  return view;
}

} // anonymous namespace

arming_preview::arming_preview(resources::archive const &game, resources::executable_tables const &tables, flight::player_aircraft const selected) :
  resources{game}, aircraft{resources.object(tables.arming_art().preview_names.at(std::to_underlying(selected) - 1))},
  miniature{resources.object(tables.arming_art().preview_names.at(std::to_underlying(selected) - 1))}, assets{tables.arming_art()}, definitions{tables.weapons} {
  // The original arming startup issues event 5 after fading in. F-117/F-22 use it to open the bays.
}
void arming_preview::start() {
  aircraft.execute(5);
}
vec3<int16_t> arming_preview::pointer_point(vec2<int16_t> const &position) {
  // Native placement at 898EC/89927 maps mouse X to world X and mouse Y to world Z.
  return {static_cast<int16_t>(640 - 4 * position.x),130,static_cast<int16_t>(400 - 4 * position.y)};
}
std::optional<unsigned int> arming_preview::pick(vec3<int16_t> const &previous, vec3<int16_t> const &current) {
  // Native 0xb76a8 subtracts the arming aircraft's query origin (0,0,160),
  // then executes the dedicated *_glob SSD's collision entry. Its zone is the mount number.
  vec3<int16_t> constexpr query_origin{0,0,160};
  auto const result{aircraft.execute(2,{
    .movement{
      .previous{previous - query_origin},
      .current{current - query_origin},
    },
  })};
  return result.zone >= 0 && result.zone < static_cast<int>(flight::store_slots) ? std::optional{static_cast<unsigned int>(result.zone)} : std::nullopt;
}
void arming_preview::advance() {
  // Arming explicitly holds native AAC90 at one: these streams advance per model draw.
  aircraft.animate();
}
uint8_t arming_preview::bay_position() const { return aircraft.parts.front().parameters[1]; }
void arming_preview::shape(render::software_renderer &renderer, models::shape const &program, render::camera const &view,
  vec3<int32_t> const &origin, vec3<math::angle> const &angles, std::span<uint8_t const> const parameters,
  std::span<models::shape const *const> const attachments) {
  auto const projection{view.projector()};
  render::model_transform const transform{projection.matrix,angles,origin};
  models::shape_context context;
  context.distance = render::measure_model(origin,program.sort_depth_bias).distance;
  if(auto const *detail{program.detail_for_distance(context.distance)}) context.entry_address = detail->offset + 2;
  std::ranges::copy(parameters,context.parameters.begin());
  context.initial_state = parameters.empty() ? 0 : parameters.front();
  // Preserve the native Q15 model products and camera translation together.
  // Scaling only the local vertices halved every preview relative to its camera.
  context.camera.emplace(models::shape_camera{
    .basis{mat3<int32_t>{transform.matrix()}},
    .origin{vec3<int32_t>{origin}},
    .projection_shift{render::projection_shift(view.opening)},
  });
  context.attachments = attachments;
  context.project = [&](vec3d const &vertex, double const scale) {
    auto point{vec3d{vertex}};
    if(std::abs(point.z) < view.near_distance * scale) point.z = std::copysign(view.near_distance * scale,point.z);
    return view.project(point,scale);
  };
  context.face_visibility = [&view](std::span<models::model_vertex const> const vertices, models::facing_test const purpose) {
    return render::model_facing(vertices,view,purpose);
  };
  auto const geometry{models::interpret(program,context)};
  for(auto const &primitive : geometry.primitives) {
    std::vector<models::model_vertex> vertices;
    vertices.reserve(primitive.vertices.size());
    for(auto const &vertex : primitive.vertices) vertices.push_back({
      .position{vec3d{vertex.position}},
      .uv{vec2d{vertex.uv}},
      .shade{vertex.shade},
      .projection_scale{vertex.projection_scale},
    });
    uint8_t colour_row{render::distance_colour_row(origin.z)};
    if(primitive.palette == models::palette_source::fixed) colour_row = 0;
    else if(primitive.palette == models::palette_source::face_depth) colour_row = render::distance_colour_row(static_cast<int32_t>(primitive.palette_depth) * 65536);
    renderer.primitive(primitive,vertices,view,primitive.texture ? resources.texture(*primitive.texture) : std::span<uint8_t const>{},primitive.palette == models::palette_source::direct ? nullptr : &resources.model_colours(colour_row));
  }
}
void arming_preview::object(render::software_renderer &renderer, world::instance &actor, render::camera const &view,
  vec3d const &position, vec3<math::angle> const &angles, std::span<models::shape const *const> const attachments) {
  auto const projection{view.projector()};
  vec3<int32_t> const assembly{position * 65536};
  for(auto const &draw : actor.execute(1).draws) {
    auto const &part{draw.part};
    // The arming SSDs place their component anchors in world axes, separately
    // from body rotation. Rotating the F-117/F-22 offsets swung the cursor off
    // its intended centre as the little aircraft turned.
    auto const placement{world::place_model_part(projection,assembly,vec3<int16_t>{draw.anchor},0,draw.placement,actor.bounding_radius())};
    shape(renderer,resources.shape(part.name),view,render::scale_model_cache(placement.camera_origin,part.rotation_mode),world::model_orientation(angles,part),part.parameters,attachments);
  }
}
void arming_preview::draw_models(render::software_renderer &renderer, arming_state const &state, weapons::armament const &inventory, std::span<bool const> const previews) {
  std::array<models::shape const*,flight::store_slots> attachments{};
  for(unsigned int slot{0}; slot != attachments.size(); ++slot) {
    auto const &store{inventory.pylons[slot]};
    if(previews[slot]) attachments[slot] = &resources.shape(assets.empty_model);
    else if(store.visible && store.weapon != weapons::empty_pylon) attachments[slot] = &resources.shape(definitions[store.weapon].carried);
  }
  auto const view{aircraft_view(state)};
  clipped(renderer,[&] { object(renderer,aircraft,view,aircraft_position,{0,0,0},attachments); });
  thumbnail_rotation = static_cast<math::angle>(thumbnail_rotation + 512);
  for(unsigned int row{0}; row != assets.rows.size(); ++row) {
    auto const &bounds{assets.rows[row]};
    auto const weapon{state.first_store + row};
    weapon_rotations[weapon] = thumbnail_rotation;
    vec2d const centre{vec2<int>{(bounds.minimum.x + bounds.maximum.x) / 2,(bounds.minimum.y + bounds.maximum.y) / 2}};
    auto const thumbnail{render::orbit_camera({0,0x6000,0},880,centre)};
    shape(renderer,resources.shape(definitions[weapon].carried),thumbnail,thumbnail.projector().camera_fixed({0,0,0}),{0,0,thumbnail_rotation},{});
  }
}
void arming_preview::draw_cursor(render::software_renderer &renderer, arming_state const &state, vec2<int16_t> const &pointer) {
  if(state.mode == arming_mode::placing && state.selected) {
    auto const weapon{std::to_underlying(*state.selected)};
    auto const view{aircraft_view(state)};
    clipped(renderer,[&] { shape(renderer,resources.shape(definitions[weapon].carried),view,view.projector().camera_fixed(vec3<int32_t>{pointer_point(pointer)} * 65536),{0,0,weapon_rotations[weapon]},{}); });
  } else if(state.mode == arming_mode::clearing) {
    auto const view{aircraft_view(state)};
    clipped(renderer,[&] { shape(renderer,resources.shape(assets.empty_model),view,view.projector().camera_fixed(vec3<int32_t>{pointer_point(pointer)} * 65536),{0,0,0},{}); });
  } else if(state.mode == arming_mode::idle) {
    auto const miniature_view{render::orbit_camera({0,0x4000,0x2000},8000,vec2d{pointer})};
    object(renderer,miniature,miniature_view,{0,0,0},{0,0,static_cast<math::angle>(state.pulse << 8)});
  }
}

} // namespace tfx::presentation
