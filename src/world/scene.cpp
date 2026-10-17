#include "scene.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <vector>

namespace tfx::world {

scene::scene(environment const &environment, assets &bank) : terrain{environment}, resources{bank} {
}

scene_handle scene::create_actor(std::string const &name, vec3d const &position, vec3<math::angle> const &angles) {
  auto const &source{resources.object(name)};
  unsigned int const id{next_actor++};
  actors.emplace(id,moving_instance{
    .state{source},
    .position{vec3d{position}},
    .rotation{math::rotation(angles)},
  });
  return {.value{id}};
}

void scene::place_actor(scene_handle const handle, vec3d const &position, vec3<math::angle> const &angles) {
  auto &actor{actors.at(handle.value)};
  actor.position = position;
  actor.rotation = math::rotation(angles);
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
void scene::emit_effect(scene_request const &request, vec3d const &origin, math::angle const heading) {
  unsigned int constexpr emit_effect_opcode{79};
  if(!effect_sink || request.opcode != emit_effect_opcode) return;
  auto const &a{request.arguments};
  if(a.size() != 4 || a[3] >= effect_kind_count) throw std::runtime_error{"invalid authored SSD effect request"};
  auto const world_origin{word_position({std::floor(origin.x),std::floor(origin.y),std::floor(origin.z)})};
  effect_sink({
    .position{effect_origin({math::signed_word(a[0]),math::signed_word(a[1]),math::signed_word(a[2])},world_origin,heading)},
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
    .rotation{math::rotation(angles)},
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
  return state.animate({
    .status{terrain.lighting.status},
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
  for(auto &[index, instance] : instances) {
    auto const x{index % map_width}, z{index / map_width};
    result.eject_player |= advance_instance(instance,{(x + .5) * cell_units,0,(z + .5) * cell_units},terrain.tile(x,z).rotation);
  }
  for(auto &[_, actor] : actors) result.eject_player |= advance_instance(actor.state,actor.position);
  return result;
}

void scene::draw(render::software_renderer &renderer, render::camera const &view, unsigned int const radius, std::function<void()> const &final_submissions) {
  /// Queue complete model parts by camera depth plus their native signed sort bias; keep primitive order inside each part
  struct queued_part {
    models::shape const *shape;
    model_part const *part;
    vec3d origin;
    mat3d rotation;
    math::angle heading;
    double depth;
    double sort_key;
  };
  std::vector<queued_part> queue;
  int const centre_x{static_cast<int>(std::floor(view.position.x / cell_units))}, centre_z{static_cast<int>(std::floor(view.position.z / cell_units))};
  int const first_x{std::max(0, centre_x - static_cast<int>(radius))}, last_x{std::min(static_cast<int>(map_width) - 1, centre_x + static_cast<int>(radius))};
  int const first_z{std::max(0, centre_z - static_cast<int>(radius))}, last_z{std::min(static_cast<int>(map_height) - 1, centre_z + static_cast<int>(radius))};
  parts_drawn = 0;
  primitives_drawn = 0;
  for(int x{first_x}; x <= last_x; ++x) {
    for(int z{first_z}; z <= last_z; ++z) {
      auto const col{static_cast<unsigned int>(x)}, row{static_cast<unsigned int>(z)};
      auto const &tile{terrain.tile(col,row)};
      vec3d const centre{(x + .5) * cell_units,0,(z + .5) * cell_units};
      auto const camera_centre{view.transform(centre)};
      if(camera_centre.z < -cell_units || camera_centre.z > view.far_distance + cell_units) continue;
      try {
        auto &instance{terrain_instance(col,row)};
        auto const requests{[&](scene_request const &request) { emit_effect(request,centre,tile.rotation); }};
        instance_context const context{
          .status{terrain.lighting.status},
          .anchor_distance{[&](vec3d const &anchor) { return math::distance_word(word_position(centre + math::rotate_tile(anchor,tile.rotation) - view.position)); }},
          .request_output{requests},
        };
        auto const output{instance.execute(1,context)};
        for(auto const &draw : output.draws) {
          if(draw.kind == part_draw_kind::ground_shadow) continue;
          auto const &part{instance.parts.at(draw.slot)};
          if(part.name.empty()) continue;
          auto const &shape{resources.shape(part.name)};
          auto const origin{centre + math::rotate_tile(draw.anchor,tile.rotation)};
          auto const depth{view.transform(origin).z};
          queue.push_back({
            .shape{&shape},
            .part{&part},
            .origin{vec3d{origin}},
            .rotation{math::rotation(part.rotation)},
            .heading{tile.rotation},
            .depth{depth},
            .sort_key{depth + shape.sort_depth_bias},
          });
        }
      } catch(std::exception const &error) {
        warnings.insert(terrain.variant(col,row) + ": " + error.what());
      }
    }
  }
  auto const submit{[&](moving_instance &actor, vec3d const &position, mat3d const &rotation) {
    // Native moving SSD effect placement retains quarter-turn zero; its full
    // visual Euler transform is separate from the request callback.
    auto const requests{[&](scene_request const &request) { emit_effect(request,position); }};
    instance_context const context{
      .status{terrain.lighting.status},
      .anchor_distance{[&](vec3d const &anchor) { return math::distance_word(word_position(position + rotation * anchor - view.position)); }},
      .request_output{requests},
    };
    auto const output{actor.state.execute(1,context)};
    for(auto const &draw : output.draws) {
      if(draw.kind == part_draw_kind::ground_shadow) continue;
      auto const &part{actor.state.parts.at(draw.slot)};
      if(part.name.empty()) continue;
      try {
        auto const &shape{resources.shape(part.name)};
        auto const origin{position + rotation * draw.anchor};
        auto const depth{view.transform(origin).z};
        if(depth < -cell_units || depth > view.far_distance + cell_units) continue;
        queue.push_back({
          .shape{&shape},
          .part{&part},
          .origin{vec3d{origin}},
          .rotation{rotation * math::rotation(part.rotation)},
          .heading{0},
          .depth{depth},
          .sort_key{depth + shape.sort_depth_bias},
        });
      } catch(std::exception const &error) {
        warnings.insert(part.name + ": " + error.what());
      }
    }
  }};
  for(auto &[_, actor] : actors) if(actor.visible) submit(actor,actor.position,actor.rotation);
  // Gather effects after world SSD execution so newly emitted/reused slots
  // join this frame with their current state, before the global depth sort.
  if(final_submissions) final_submissions();
  for(auto const &submission : submissions) submit(actors.at(submission.handle.value),submission.position,submission.rotation);
  submissions.clear();
  std::stable_sort(queue.begin(),queue.end(),[](auto const &a, auto const &b){ return a.sort_key > b.sort_key; });
  for(auto const &item : queue) {
    try {
      auto const placed{[&item](vec3d const &vertex){ return item.origin + math::rotate_tile(item.rotation * vertex,item.heading); }};
      models::shape_context context;
      std::copy(item.part->parameters.begin(),item.part->parameters.end(),context.parameters.begin());
      // Native 0xcc001 queues parameter 0; 0xbac16 seeds the shape condition from it.
      context.initial_state = item.part->parameters.front();
      context.status = terrain.lighting.status;
      context.jitter = &working_jitter;
      context.distance = static_cast<int16_t>(std::clamp(item.depth,-32768.0,32767.0));
      context.project = [&view, &placed](vec3d const &v, double const scale){
        auto point{view.transform(placed(v))};
        if(std::abs(point.z) < view.near_distance * scale) point.z = std::copysign(view.near_distance * scale,point.z);
        return view.project(point,scale);
      };
      auto const geometry{models::interpret(*item.shape,context)};
      warnings.insert(geometry.warnings.begin(),geometry.warnings.end());
      ++parts_drawn;
      for(auto const &primitive : geometry.primitives) {
        std::vector<models::model_vertex> vertices;
        vertices.reserve(primitive.vertices.size());
        for(auto const &vertex : primitive.vertices) vertices.push_back({
          .position{view.transform(placed(vertex.position))},
          .uv{vec2d{vertex.uv}},
          .shade{vertex.shade},
          .projection_scale{vertex.projection_scale},
        });
        auto const texture{primitive.texture ? resources.texture(*primitive.texture) : std::span<uint8_t const>{}};
        if(primitive.texture && texture.empty()) warnings.insert("unresolved runtime texture: " + item.part->name);
        renderer.primitive(primitive,vertices,view,texture);
        ++primitives_drawn;
      }
    } catch(std::exception const &error) {
      warnings.insert(item.part->name + ": " + error.what());
    }
  }
}

} // namespace tfx::world
