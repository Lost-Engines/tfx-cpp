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

unsigned int wrapped_cell(int const value, unsigned int const dimension) {
  /// Native 0xb0cbc uses dimension - 1 for negative remainders, including its one-cell seam quirk.
  int const remainder{value % static_cast<int>(dimension)};
  return static_cast<unsigned int>(remainder < 0 ? remainder + static_cast<int>(dimension) - 1 : remainder);
}

} // anonymous namespace

instance &scene::terrain_instance(unsigned int const x, unsigned int const z) {
  auto const &source{resources.object(terrain.variant(x,z))};
  return instances.try_emplace(z * map_width + x,source).first->second;
}

void scene::prepare_terrain_cell(unsigned int const x, unsigned int const z) {
  terrain_instance(x,z);
}

instance_result scene::terrain_event(unsigned int const x, unsigned int const z, unsigned int const entry) {
  return terrain_instance(x,z).execute(entry,{
    .status{terrain.status},
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
  return state.execute(2,{
    .movement{
      .previous{word_position(math::rotate_tile(vec3d{previous} - origin,inverse_heading))},
      .current{word_position(math::rotate_tile(vec3d{current} - origin,inverse_heading))},
    },
    .player_query{player},
    .impact_damage{damage},
    .status{terrain.status},
    .collision_response{std::move(response)},
  });
}

instance_result scene::collide_actor(scene_handle const handle, vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t const damage, std::function<void(uint16_t)> response, std::function<void(int)> damage_response) {
  auto &actor{actors.at(handle.value)};
  // Native moving assemblies retain axis-aligned SSD collision volumes; their full visual Euler rotation is separate.
  vec3d const origin{std::floor(actor.position.x),std::floor(actor.position.y),std::floor(actor.position.z)};
  return actor.state.execute(2,{
    .movement{
      .previous{word_position(vec3d{previous} - origin)},
      .current{word_position(vec3d{current} - origin)},
    },
    .impact_damage{damage},
    .status{terrain.status},
    .collision_response{std::move(response)},
    .damage_response{std::move(damage_response)},
  });
}

void scene::apply_actor_contact_damage(scene_handle const handle, uint16_t const damage) {
  actors.at(handle.value).state.apply_contact_damage(damage);
}

bool scene::actor_destroyed(scene_handle const handle) const {
  return actors.at(handle.value).state.destroyed;
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
  return actors.at(handle.value).state.execute(entry,{
    .status{terrain.status},
  });
}

void scene::advance_instance(instance &state) {
  state.animate({
    .status{terrain.status},
  });
}

void scene::advance(timer_ticks const elapsed) {
  /// Each static or moving instance owns independent streams; the native clock gate remains shared
  bool const animate{clock.advance(elapsed)};
  if(animate) saved_jitter = working_jitter;
  else working_jitter = saved_jitter;
  if(!animate) return;
  for(auto &[_, instance] : instances) advance_instance(instance);
  for(auto &[_, actor] : actors) advance_instance(actor.state);
}

void scene::draw(render::software_renderer &renderer, render::camera const &view, unsigned int const radius) {
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
        instance_context const context{
          .status{terrain.status},
          .anchor_distance{[&](vec3d const &anchor) { return math::distance_word(word_position(centre + math::rotate_tile(anchor,tile.rotation) - view.position)); }},
        };
        for(auto const &draw : instance.execute(1,context).draws) {
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
    instance_context const context{
      .status{terrain.status},
      .anchor_distance{[&](vec3d const &anchor) { return math::distance_word(word_position(position + rotation * anchor - view.position)); }},
    };
    for(auto const &draw : actor.state.execute(1,context).draws) {
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
  for(auto const &submission : submissions) submit(actors.at(submission.handle.value),submission.position,submission.rotation);
  submissions.clear();
  std::stable_sort(queue.begin(),queue.end(),[](auto const &a, auto const &b){ return a.sort_key > b.sort_key; });
  for(auto const &item : queue) {
    try {
      auto const placed{[&item](vec3d const &vertex){ return item.origin + math::rotate_tile(item.rotation * vertex,item.heading); }};
      models::shape_context context;
      std::copy(item.part->parameters.begin(),item.part->parameters.end(),context.parameters.begin());
      context.status = terrain.status;
      context.jitter = &working_jitter;
      context.distance = static_cast<int16_t>(std::clamp(item.depth,-32768.0,32767.0));
      context.project = [&view, &placed](vec3d const &v){
        auto point{view.transform(placed(v))};
        if(std::abs(point.z) < view.near_distance) point.z = std::copysign(view.near_distance,point.z);
        return view.project(point);
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
