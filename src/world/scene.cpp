#include "scene.h"
#include <algorithm>
#include <cmath>
#include <iterator>
#include <vector>

namespace tfx::world {

scene::scenery_instance::scenery_instance(definition const &source) : parts{source.parts}, all_parameters{(source.flags & 0x0100) != 0} {
  for(auto const &stream : source.streams) streams.push_back({
    .part{stream.part},
    .parameter{stream.parameter},
    .player{stream.words},
  });
}

scene::scene(environment const &environment, assets &bank) : terrain{environment}, resources{bank} {
}

void scene::advance(timer_ticks const elapsed) {
  /// Advance local scenery streams at the native clock gate; mission/AI actor eligibility remains separate work
  bool const animate{clock.advance(elapsed)};
  if(animate) saved_jitter = working_jitter;
  else working_jitter = saved_jitter;
  if(!animate) return;
  for(auto &[_, instance] : instances) {
    for(auto &stream : instance.streams) {
      if(stream.paused || (stream.parameter && !instance.all_parameters)) continue;
      try {
        auto &parameter{instance.parts.at(stream.part).parameters.at(stream.parameter)};
        auto const result{stream.player.tick(parameter)};
        if(result.action == stream_action::event_requested) {
          stream.paused = true;
          warnings.insert("SSD event " + std::to_string(result.event) + " awaits the actor dispatcher; stream paused");
        }
      } catch(std::exception const &error) {
        stream.paused = true;
        warnings.insert(error.what());
      }
    }
  }
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
        auto const &object{resources.object(terrain.variant(col,row))};
        auto &instance{instances.try_emplace(row * map_width + col,object).first->second};
        for(auto const &draw : object.draws) {
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
