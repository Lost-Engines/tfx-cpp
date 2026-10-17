#include "scene.h"
#include "world/sky.h"
#include "world/model_placement.h"
#include "world/model_orientation.h"
#include "render/model_transform.h"
#include "render/model_metrics.h"
#include "render/model_queue.h"
#include "render/model_point.h"
#include "render/integer_model_polygon.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <vector>

namespace tfx::world {

scene::scene(environment const &environment, assets &bank, world::environment const *const upper) : terrain{environment}, upper_terrain{upper}, resources{bank} {
}

scene_handle scene::create_actor(std::string const &name, vec3d const &position, vec3<math::angle> const &angles) {
  auto const &source{resources.object(name)};
  unsigned int const id{next_actor++};
  actors.emplace(id,moving_instance{
    .state{source},
    .position{vec3d{position}},
    .angles{vec3<math::angle>{angles}},
  });
  return {.value{id}};
}

void scene::place_actor(scene_handle const handle, vec3d const &position, vec3<math::angle> const &angles) {
  auto &actor{actors.at(handle.value)};
  actor.position = position;
  actor.angles = angles;
}

void scene::show_actor(scene_handle const handle, bool const visible) {
  actors.at(handle.value).visible = visible;
}

bool scene::terrain_intact(unsigned int const x, unsigned int const z) {
  return x < map_width && z < map_height && !terrain_instance(x,z).destroyed;
}

namespace {

vec3<int16_t> word_position(vec3d const &position) {
  auto const component{[](double const value) { return math::signed_word(static_cast<uint16_t>(static_cast<int64_t>(value))); }};
  return {component(position.x),component(position.y),component(position.z)};
}

std::optional<flight::landing_port> landing_port(instance const &state) {
  int16_t constexpr landing_type{50};
  if(state.type() != landing_type) return std::nullopt;
  // Native 0xb6e48 reads the first three initialized custom words.
  return flight::landing_port{
    .offset{math::signed_word(state.custom.at(0)),math::signed_word(state.custom.at(1))},
    .heading{state.custom.at(2)},
  };
}

unsigned int wrapped_cell(int const value, unsigned int const dimension) {
  /// Native 0xb0cbc uses dimension - 1 for negative remainders, including its one-cell seam quirk.
  int const remainder{value % static_cast<int>(dimension)};
  return static_cast<unsigned int>(remainder < 0 ? remainder + static_cast<int>(dimension) - 1 : remainder);
}

} // anonymous namespace

void scene::set_effect_sink(std::function<void(effect_record const&)> sink) { effect_sink = std::move(sink); }
void scene::set_query_reference(vec3<int32_t> const *const position) { query_reference = position; }
vec3<int16_t> scene::reference_words(vec3d const &fallback) const {
  if(query_reference) return word_position(vec3d{*query_reference});
  return word_position({std::floor(fallback.x),std::floor(fallback.y),std::floor(fallback.z)});
}
void scene::emit_effect(scene_request const &request, vec3d const &origin, math::angle const heading) {
  unsigned int constexpr emit_effect_opcode{79};
  if(!effect_sink || request.opcode != emit_effect_opcode) return;
  auto const &a{request.arguments};
  if(a.size() != 4 || a[3] >= effect_kind_count) throw std::runtime_error{"invalid authored SSD effect request"};
  auto const world_origin{word_position({std::floor(origin.x),std::floor(origin.y),std::floor(origin.z)})};
  effect_sink({
    .position{place_instance_point({math::signed_word(a[0]),math::signed_word(a[1]),math::signed_word(a[2])},world_origin,heading)},
    .kind{static_cast<effect_kind>(a[3])},
  });
}

instance &scene::terrain_instance(unsigned int const x, unsigned int const z) {
  auto const &source{resources.object(terrain.variant(x,z))};
  return instances.try_emplace(z * map_width + x,source).first->second;
}

bool scene::terrain_destroyed(vec3<int32_t> const &position) {
  int const cell_x{position.x >> cell_shift}, cell_z{position.z >> cell_shift};
  auto const x{wrapped_cell(cell_x,map_width)};
  auto const z{map_height - 1 - wrapped_cell(static_cast<int>(map_height) - 1 - cell_z,map_height)};
  return terrain_instance(x,z).destroyed;
}

int16_t scene::terrain_type(vec3<int32_t> const &position) {
  int const cell_x{position.x >> 11}, cell_z{position.z >> 11};
  auto const x{wrapped_cell(cell_x,map_width)};
  auto const z{map_height - 1 - wrapped_cell(static_cast<int>(map_height) - 1 - cell_z,map_height)};
  return terrain_instance(x,z).type();
}

void scene::prepare_terrain_cell(unsigned int const x, unsigned int const z) {
  terrain_instance(x,z);
}

instance_result scene::terrain_event(unsigned int const x, unsigned int const z, unsigned int const entry) {
  vec3d const origin{(x + .5) * cell_units,0,(z + .5) * cell_units};
  auto const output{[&](scene_request const &request) { emit_effect(request,origin,terrain.tile(x,z).rotation); }};
  return terrain_instance(x,z).execute(entry,{
    .status{terrain.lighting.status},
    .request_output{output},
  });
}

instance_result scene::collide_terrain(vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t const damage, bool const player, std::function<void(uint16_t)> response) {
  int const cell_x{current.x >> 11}, cell_z{current.z >> 11};
  auto const x{wrapped_cell(cell_x,map_width)};
  auto const z{map_height - 1 - wrapped_cell(static_cast<int>(map_height) - 1 - cell_z,map_height)};
  auto const &tile{terrain.tile(x,z)};
  auto &state{terrain_instance(x,z)};
  vec3d const origin{(cell_x + .5) * cell_units,0,(cell_z + .5) * cell_units};
  auto const inverse_heading{static_cast<math::angle>(-tile.rotation)};
  auto const output{[&](scene_request const &request) { emit_effect(request,origin,tile.rotation); }};
  return state.execute(2,{
    .movement{
      .previous{word_position(math::rotate_tile(vec3d{previous} - origin,inverse_heading))},
      .current{word_position(math::rotate_tile(vec3d{current} - origin,inverse_heading))},
    },
    .player_query{player},
    .impact_damage{damage},
    .status{terrain.lighting.status},
    .collision_response{std::move(response)},
    .request_output{output},
  });
}

instance_result scene::collide_actor(scene_handle const handle, vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t const damage, std::function<void(uint16_t)> response, std::function<void(int)> damage_response, bool const player) {
  auto &actor{actors.at(handle.value)};
  // Native moving assemblies retain axis-aligned SSD collision volumes; their full visual Euler rotation is separate.
  vec3d const origin{std::floor(actor.position.x),std::floor(actor.position.y),std::floor(actor.position.z)};
  auto const output{[&](scene_request const &request) { emit_effect(request,origin); }};
  return actor.state.execute(2,{
    .movement{
      .previous{word_position(vec3d{previous} - origin)},
      .current{word_position(vec3d{current} - origin)},
    },
    .player_query{player},
    .impact_damage{damage},
    .status{terrain.lighting.status},
    .collision_response{std::move(response)},
    .damage_response{std::move(damage_response)},
    .request_output{output},
  });
}

void scene::apply_actor_contact_damage(scene_handle const handle, uint16_t const damage) {
  actors.at(handle.value).state.apply_contact_damage(damage);
}

bool scene::actor_destroyed(scene_handle const handle) const {
  return actors.at(handle.value).state.destroyed;
}

int16_t scene::actor_type(scene_handle const handle) const {
  return actors.at(handle.value).state.type();
}

std::optional<flight::landing_port> scene::terrain_landing_port(vec2<int16_t> const &cell) {
  if(cell.x < 0 || cell.y < 0 || cell.x >= static_cast<int>(map_width) || cell.y >= static_cast<int>(map_height)) return std::nullopt;
  return landing_port(terrain_instance(static_cast<unsigned int>(cell.x),static_cast<unsigned int>(cell.y)));
}

std::optional<flight::landing_port> scene::actor_landing_port(scene_handle const handle) const {
  return landing_port(actors.at(handle.value).state);
}

std::vector<vec3<int16_t>> scene::actor_damage_centres(scene_handle const handle) const {
  return actors.at(handle.value).state.damage_centres();
}

uint16_t scene::actor_impact_damage(scene_handle const handle) const {
  return actors.at(handle.value).state.impact_damage;
}

void scene::queue_actor(scene_handle const handle, vec3d const &position, vec3<math::angle> const &angles) {
  submissions.push_back({
    .handle{handle},
    .position{vec3d{position}},
    .angles{vec3<math::angle>{angles}},
  });
}

void scene::queue_model(std::string const &name, vec3d const &position) {
  model_submissions.push_back({
    .part{
      .name{name},
      .rotation{0,0,0},
    },
    .position{vec3d{position}},
  });
}

instance_result scene::actor_event(scene_handle const handle, unsigned int const entry) {
  auto &actor{actors.at(handle.value)};
  auto const output{[&](scene_request const &request) { emit_effect(request,actor.position); }};
  return actor.state.execute(entry,{
    .status{terrain.lighting.status},
    .request_output{output},
  });
}

bool scene::advance_instance(instance &state, vec3d const &origin, math::angle const heading) {
  auto const output{[&](scene_request const &request) { emit_effect(request,origin,heading); }};
  auto const placed_origin{word_position({std::floor(origin.x),std::floor(origin.y),std::floor(origin.z)})};
  auto const reference{reference_words()};
  return state.animate({
    .status{terrain.lighting.status},
    .distance{instance_point_distance({0,0,0},placed_origin,heading,reference)},
    .anchor_distance{[&](vec3d const &anchor) { return instance_point_distance(word_position(anchor),placed_origin,heading,reference); }},
    .request_output{output},
  }).ejection_requested;
}

scene_events scene::advance(timer_ticks const elapsed) {
  /// Each static or moving instance owns independent streams; the native clock gate remains shared
  bool const animate{clock.advance(elapsed)};
  if(animate) saved_jitter = working_jitter;
  else working_jitter = saved_jitter;
  scene_events result;
  if(!animate) return result;
  result.animated = true;
  for(auto &[index, instance] : instances) {
    auto const x{index % map_width}, z{index / map_width};
    result.eject_player |= advance_instance(instance,{(x + .5) * cell_units,0,(z + .5) * cell_units},terrain.tile(x,z).rotation);
  }
  if(upper_terrain) for(auto &[index, instance] : upper_instances) {
    auto const x{index % map_width}, z{index / map_width};
    int const height{select_terrain_layer(true,terrain.lighting.layer_y,terrain.lighting.layer_offset_y,terrain.lighting.layer_y).height};
    result.eject_player |= advance_instance(instance,{(x + .5) * cell_units,static_cast<double>(height),(z + .5) * cell_units},upper_terrain->tile(x,z).rotation);
  }
  for(auto &[_, actor] : actors) result.eject_player |= advance_instance(actor.state,actor.position);
  return result;
}

void scene::draw(render::software_renderer &renderer, render::camera const &view, unsigned int const radius, std::function<void()> const &final_submissions, std::optional<int32_t> const camera_anchor_y, int16_t const shadow_ground_height) {
  /// Native cached model metrics own detail, distance predicates, remap and signed sort priority
  struct queued_part {
    models::shape const *shape;
    std::string name;
    std::array<uint8_t,part_parameters> parameters;
    vec3d origin;
    mat3d rotation;
    math::angle heading;
    vec3<math::angle> angles;
    double depth;
    double sort_key;
    vec3<int32_t> camera_origin;
    render::model_metrics metrics;
    render::model_render_path path;
    uint8_t rotation_scale;
  };
  std::vector<queued_part> queue;
  render::model_queue native_queue;
  auto const projection{view.projector()};
  bool const native{view.projection == render::projection_mode::original_model};
  auto const fixed_position{[](vec3d const &position) { return vec3<int32_t>{vec3<uint32_t>{vec3<int64_t>{position * 65536}}}; }};
  auto const paint_part{[&](queued_part &item, render::model_render_path const path, part_delivery const delivery = part_delivery::queued) {
    try {
      if(native && delivery == part_delivery::queued) model_parameters = item.parameters;
      if(native) item.camera_origin = render::scale_model_cache(item.camera_origin,item.rotation_scale);
      item.metrics.distance = render::measure_model(item.camera_origin,item.shape->sort_depth_bias).distance;
      auto const *detail{native ? item.shape->detail_for_distance(item.metrics.distance) : nullptr};
      if(native && !detail) return;
      bool const shadow{path == render::model_render_path::ground_shadow};
      if(shadow && detail && detail->kind != models::detail_kind::polygon) return;
      if(detail && detail->kind >= models::detail_kind::pixel_block) {
        unsigned int const size{detail->kind == models::detail_kind::pixel_block ? 2u : 1u};
        render::model_point(renderer.output,item.camera_origin,view,size,resources.model_colours(item.metrics.colour_row)[detail->colour]);
        ++parts_drawn;++primitives_drawn;
        return;
      }
      auto const placed{[&item](vec3d const &vertex){ return item.origin + math::rotate_tile(item.rotation * vertex,item.heading); }};
      render::model_transform const transform{projection.matrix,path == render::model_render_path::unrotated ? vec3<math::angle>{0,0,0} : vec3<math::angle>{item.angles},item.camera_origin,shadow ? render::model_surface::ground_shadow : render::model_surface::body};
      auto const camera_point{[&](vec3d const &position, double const scale) { if(native) return transform.point(position,scale);auto point{placed(position)};if(shadow) point.y = item.origin.y;return view.transform(point); }};
      models::shape_context context;
      auto const &parameters{native ? model_parameters : item.parameters};
      std::copy(parameters.begin(),parameters.end(),context.parameters.begin());
      // Native 0xcc001 queues parameter 0; 0xbac16 seeds the shape condition from it.
      context.initial_state = item.parameters.front();
      context.status = terrain.lighting.status;
      context.jitter = &working_jitter;
      context.distance = native ? item.metrics.distance : static_cast<int16_t>(std::clamp(item.depth,-32768.0,32767.0));
      if(detail) context.entry_address = detail->offset + 2;
      context.project = [&view, &camera_point](vec3d const &v, double const scale){
        auto point{camera_point(v,scale)};
        if(std::abs(point.z) < view.near_distance * scale) point.z = std::copysign(view.near_distance * scale,point.z);
        return view.project(point,scale);
      };
      if(view.projection == render::projection_mode::original_model) context.face_visibility = [&view,&camera_point](std::span<models::model_vertex const> const vertices, models::facing_test const purpose) {
        std::vector<models::model_vertex> camera;
        camera.reserve(vertices.size());
        for(auto const &vertex : vertices) camera.push_back({
          .position{camera_point(vertex.position,vertex.projection_scale)},
          .uv{0,0},
          .projection_scale{vertex.projection_scale},
        });
        return render::model_facing(camera,view,purpose);
      };
      auto const geometry{models::interpret(*item.shape,context)};
      warnings.insert(geometry.warnings.begin(),geometry.warnings.end());
      ++parts_drawn;
      for(auto const &primitive : geometry.primitives) {
        std::vector<models::model_vertex> vertices;
        vertices.reserve(primitive.vertices.size());
        for(auto const &vertex : primitive.vertices) vertices.push_back({
          .position{camera_point(vertex.position,vertex.projection_scale)},
          .uv{vec2d{vertex.uv}},
          .shade{shadow ? -1 : vertex.shade},
          .projection_scale{vertex.projection_scale},
        });
        if(shadow) {
          auto silhouette{primitive};silhouette.colour = 0;silhouette.texture.reset();
          renderer.primitive(silhouette,vertices,view,{});
          ++primitives_drawn;continue;
        }
        auto const texture{primitive.texture ? resources.texture(*primitive.texture) : std::span<uint8_t const>{}};
        if(primitive.texture && texture.empty()) warnings.insert("unresolved runtime texture: " + item.name);
        renderer.primitive(primitive,vertices,view,texture,view.projection == render::projection_mode::original_model ? &resources.model_colours(item.metrics.colour_row) : nullptr);
        ++primitives_drawn;
      }
    } catch(std::exception const &error) {
      warnings.insert(item.name + ": " + error.what());
    }
  }};
  auto const queue_part{[&](models::shape const &shape, model_part const &part, vec3d const &origin, mat3d const &rotation, math::angle const heading, vec3<math::angle> const &angles, vec3<int32_t> const &camera_origin, render::model_render_path const path = render::model_render_path::scaled, part_delivery const delivery = part_delivery::queued) {
    auto const metrics{render::measure_model(camera_origin,shape.sort_depth_bias)};
    double const depth{view.transform(origin).z};
    queued_part item{
      .shape{&shape},
      .name{part.name},
      .parameters{part.parameters},
      .origin{vec3d{origin}},
      .rotation{mat3d{rotation}},
      .heading{heading},
      .angles{vec3<math::angle>{angles}},
      .depth{depth},
      .sort_key{native ? metrics.order : depth + shape.sort_depth_bias},
      .camera_origin{vec3<int32_t>{camera_origin}},
      .metrics{metrics},
      .path{path},
      .rotation_scale{part.rotation_mode ? part.rotation_mode : uint8_t{1}},
    };
    if(native && delivery == part_delivery::immediate) {
      auto const slot{native_queue.scratch_slot()};
      auto const state{model_slots.immediate(slot,item.rotation_scale)};
      item.path = state.path;item.rotation_scale = state.scale;
      if(slot < queue.size()) queue[slot] = std::move(item);
      else queue.push_back(std::move(item));
      paint_part(queue[slot],path,part_delivery::immediate);
      return;
    }
    if(native) {
      auto const slot{native_queue.insert(metrics.order)};
      auto const state{model_slots.queued(slot,path,item.rotation_scale)};
      item.path = state.path;item.rotation_scale = state.scale;
      if(slot < queue.size()) queue[slot] = std::move(item);
      else queue.push_back(std::move(item));
    } else queue.push_back(std::move(item));
  }};
  // Native 0x7589a binds SSD range queries to the player, independently of the
  // camera. Standalone inspection scenes use their camera as the reference.
  auto const reference{reference_words(view.position)};
  int const centre_x{static_cast<int>(std::floor(view.position.x / cell_units))}, centre_z{static_cast<int>(std::floor(view.position.z / cell_units))};
  int const first_x{std::max(0, centre_x - static_cast<int>(radius))}, last_x{std::min(static_cast<int>(map_width) - 1, centre_x + static_cast<int>(radius))};
  int const first_z{std::max(0, centre_z - static_cast<int>(radius))}, last_z{std::min(static_cast<int>(map_height) - 1, centre_z + static_cast<int>(radius))};
  auto const layer{select_terrain_layer(upper_terrain && terrain.lighting.cloud_layer,terrain.lighting.layer_y,terrain.lighting.layer_offset_y,camera_anchor_y.value_or(static_cast<int32_t>(std::floor(view.position.y))))};
  auto const &grid{layer.upper ? *upper_terrain : terrain};
  auto &states{layer.upper ? upper_instances : instances};
  parts_drawn = 0;
  primitives_drawn = 0;
  for(int x{first_x}; x <= last_x; ++x) {
    for(int z{first_z}; z <= last_z; ++z) {
      auto const col{static_cast<unsigned int>(x)}, row{static_cast<unsigned int>(z)};
      auto const &tile{grid.tile(col,row)};
      vec3d const centre{(x + .5) * cell_units,static_cast<double>(layer.height),(z + .5) * cell_units};
      auto const camera_centre{view.transform(centre)};
      if(!native && (camera_centre.z < -cell_units || camera_centre.z > view.far_distance + cell_units)) continue;
      try {
        auto &instance{states.try_emplace(row * map_width + col,resources.object(grid.variant(col,row))).first->second};
        auto const assembly{fixed_position(centre)};
        if(native && !projection.camera_sphere_visible(projection.camera_fixed(assembly),instance.bounding_radius())) continue;
        auto const requests{[&](scene_request const &request) { emit_effect(request,centre,tile.rotation); }};
        auto const origin{word_position(centre)};
        instance_context const context{
          .status{terrain.lighting.status},
          .distance{instance_point_distance({0,0,0},origin,tile.rotation,reference)},
          .anchor_distance{[&](vec3d const &anchor) { return instance_point_distance(word_position(anchor),origin,tile.rotation,reference); }},
          .request_output{requests},
        };
        auto const output{instance.execute(1,context)};
        for(auto const &draw : output.draws) {
          bool const shadow{draw.kind == part_draw_kind::ground_shadow};
          auto const shadow_placement{shadow ? place_model_shadow(projection,assembly,shadow_ground_height,instance.bounding_radius()) : std::optional<model_placement>{}};
          if(shadow && (!shadow_placement || !shadow_placement->visible)) continue;
          auto const &part{draw.part};
          if(part.name.empty()) continue;
          auto const &shape{resources.shape(part.name)};
          auto const placement{shadow ? *shadow_placement : place_model_part(projection,assembly,word_position(draw.anchor),tile.rotation,draw.placement,instance.bounding_radius())};
          if(native && !placement.visible) continue;
          auto const origin{(shadow || (native && draw.placement != part_position::assembly_origin)) ? vec3d{effect_position(placement.position,vec3<int32_t>{centre})} : centre + math::rotate_tile(draw.anchor,tile.rotation)};
          queue_part(shape,part,origin,math::rotation(part.rotation),tile.rotation,model_orientation({0,0,0},part,tile.rotation,draw.orientation),placement.camera_origin,shadow ? render::model_render_path::ground_shadow : render::model_render_path::scaled,draw.delivery);
        }
      } catch(std::exception const &error) {
        warnings.insert(grid.variant(col,row) + ": " + error.what());
      }
    }
  }
  auto const submit{[&](moving_instance &actor, vec3d const &position, vec3<math::angle> const &angles) {
    auto const rotation{math::rotation(angles)};
    // Native moving SSD effect placement retains quarter-turn zero; its full
    // visual Euler transform is separate from the request callback.
    auto const assembly{fixed_position(position)};
    if(native && !projection.camera_sphere_visible(projection.camera_fixed(assembly),actor.state.bounding_radius())) return;
    auto const requests{[&](scene_request const &request) { emit_effect(request,position); }};
    auto const origin{word_position({std::floor(position.x),std::floor(position.y),std::floor(position.z)})};
    instance_context const context{
      .status{terrain.lighting.status},
      .distance{instance_point_distance({0,0,0},origin,0,reference)},
      .anchor_distance{[&](vec3d const &anchor) { return instance_point_distance(word_position(anchor),origin,0,reference); }},
      .request_output{requests},
    };
    auto const output{actor.state.execute(1,context)};
    for(auto const &draw : output.draws) {
      bool const shadow{draw.kind == part_draw_kind::ground_shadow};
      auto const shadow_placement{shadow ? place_model_shadow(projection,assembly,shadow_ground_height,actor.state.bounding_radius()) : std::optional<model_placement>{}};
      if(shadow && (!shadow_placement || !shadow_placement->visible)) continue;
      auto const &part{draw.part};
      if(part.name.empty()) continue;
      try {
        auto const &shape{resources.shape(part.name)};
        auto const placement{shadow ? *shadow_placement : place_model_part(projection,assembly,word_position(draw.anchor),0,draw.placement,actor.state.bounding_radius())};
        if(native && !placement.visible) continue;
        auto const origin{(shadow || (native && draw.placement != part_position::assembly_origin)) ? vec3d{effect_position(placement.position,vec3<int32_t>{position})} : position + rotation * draw.anchor};
        double const depth{view.transform(origin).z};
        if(!native && (depth < -cell_units || depth > view.far_distance + cell_units)) continue;
        queue_part(shape,part,origin,rotation * math::rotation(part.rotation),0,model_orientation(angles,part),placement.camera_origin,shadow ? render::model_render_path::ground_shadow : render::model_render_path::scaled,draw.delivery);
      } catch(std::exception const &error) {
        warnings.insert(part.name + ": " + error.what());
      }
    }
  }};
  for(auto &[_, actor] : actors) if(actor.visible) submit(actor,actor.position,actor.angles);
  // Gather effects after world SSD execution so newly emitted/reused slots
  // join this frame with their current state, before the global depth sort.
  if(final_submissions) final_submissions();
  for(auto const &submission : submissions) submit(actors.at(submission.handle.value),submission.position,submission.angles);
  submissions.clear();
  for(auto const &submission : model_submissions) {
    auto const &shape{resources.shape(submission.part.name)};
    mat3d const identity{1.,0.,0.,0.,1.,0.,0.,0.,1.};
    queue_part(shape,submission.part,submission.position,identity,0,{0,0,0},projection.camera_integer(vec3<int32_t>{submission.position}),render::model_render_path::unrotated);
  }
  if(!native) std::stable_sort(queue.begin(),queue.end(),[](auto const &a, auto const &b){ return a.sort_key > b.sort_key; });
  auto const order{native ? native_queue.draw_order() : std::vector<render::model_slot>{}};
  unsigned int const count{native ? native_queue.size() : static_cast<unsigned int>(queue.size())};
  for(unsigned int draw_index{0}; draw_index != count; ++draw_index) {
    auto &item{queue[native ? static_cast<unsigned int>(order[draw_index]) : draw_index]};
    paint_part(item,item.path);
  }
  model_submissions.clear();
}

} // namespace tfx::world
