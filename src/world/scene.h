#pragma once

#include <map>
#include <set>
#include <string>
#include "render/software_renderer.h"
#include "world/animation.h"
#include "world/assets.h"
#include "world/environment.h"
#include "world/instance.h"
#include "flight/landing.h"

namespace tfx::world {

struct scene_handle { unsigned int value; };

class scene {
private:
  environment const &terrain;
  assets &resources;
  std::map<unsigned int,instance> instances;
  struct moving_instance {
    instance state;
    vec3d position;
    mat3d rotation;
    bool visible{true};
  };
  std::map<unsigned int,moving_instance> actors;
  unsigned int next_actor{0};
  instance &terrain_instance(unsigned int x, unsigned int z);
  void advance_instance(instance &state);
  struct actor_submission {
    scene_handle handle;
    vec3d position;
    mat3d rotation;
  };
  std::vector<actor_submission> submissions;
  animation_clock clock;
  math::jitter_state working_jitter;
  math::jitter_state saved_jitter;

public:
  std::set<std::string> warnings;
  unsigned int parts_drawn{0};
  unsigned int primitives_drawn{0};
  scene(environment const &terrain, assets &resources);
  scene_handle create_actor(std::string const &definition, vec3d const &position, vec3<math::angle> const &angles);
  void place_actor(scene_handle handle, vec3d const &position, vec3<math::angle> const &angles);
  void show_actor(scene_handle handle, bool visible);
  bool terrain_intact(unsigned int x, unsigned int z);
  instance_result collide_terrain(vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t damage = 0, bool player = true, std::function<void(uint16_t)> response = {});
  instance_result collide_actor(scene_handle handle, vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t damage, std::function<void(uint16_t)> response = {}, std::function<void(int)> damage_response = {}, bool player = false);
  void apply_actor_contact_damage(scene_handle handle, uint16_t damage);
  bool actor_destroyed(scene_handle handle) const;
  int16_t actor_type(scene_handle handle) const;
  std::optional<flight::landing_port> terrain_landing_port(vec2<int16_t> const &cell);
  std::optional<flight::landing_port> actor_landing_port(scene_handle handle) const;
  std::vector<vec3<int16_t>> actor_damage_centres(scene_handle handle) const;
  uint16_t actor_impact_damage(scene_handle handle) const;
  void queue_actor(scene_handle handle, vec3d const &position, vec3<math::angle> const &angles);
  instance_result actor_event(scene_handle handle, unsigned int entry);
  void prepare_terrain_cell(unsigned int x, unsigned int z);
  instance_result terrain_event(unsigned int x, unsigned int z, unsigned int entry);
  void advance(timer_ticks elapsed);
  void draw(render::software_renderer &renderer, render::camera const &view, unsigned int radius);
};

} // namespace tfx::world
