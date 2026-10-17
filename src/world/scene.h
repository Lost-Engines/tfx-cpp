#pragma once

#include <map>
#include <set>
#include <string>
#include "render/software_renderer.h"
#include "world/animation.h"
#include "world/assets.h"
#include "world/environment.h"
#include "world/instance.h"
#include "world/effects.h"
#include "flight/landing.h"

namespace tfx::world {

struct scene_handle {
  unsigned int value;
  bool operator==(scene_handle const&) const = default;
};
struct scene_events {
  bool animated{false};
  bool eject_player{false};
};

class scene {
private:
  environment const &terrain;
  environment const *upper_terrain;
  assets &resources;
  std::map<unsigned int,instance> instances, upper_instances;
  struct moving_instance {
    instance state;
    vec3d position;
    mat3d rotation;
    bool visible{true};
  };
  std::map<unsigned int,moving_instance> actors;
  unsigned int next_actor{0};
  instance &terrain_instance(unsigned int x, unsigned int z);
  std::function<void(effect_record const&)> effect_sink{};
  vec3<int32_t> const *query_reference{nullptr}; // Borrowed from the mission player.
  vec3<int16_t> reference_words(vec3d const &fallback = {0,0,0}) const;
  void emit_effect(scene_request const &request, vec3d const &origin, math::angle heading = 0);
  bool advance_instance(instance &state, vec3d const &origin, math::angle heading = 0);
  struct actor_submission {
    scene_handle handle;
    vec3d position;
    mat3d rotation;
  };
  std::vector<actor_submission> submissions;
  struct model_submission {
    model_part part;
    vec3d position;
  };
  std::vector<model_submission> model_submissions;
  animation_clock clock;
  math::jitter_state working_jitter;
  math::jitter_state saved_jitter;

public:
  std::set<std::string> warnings;
  unsigned int parts_drawn{0};
  unsigned int primitives_drawn{0};
  scene(environment const &terrain, assets &resources, environment const *upper = nullptr);
  void set_effect_sink(std::function<void(effect_record const&)> sink);
  void set_query_reference(vec3<int32_t> const *position);
  scene_handle create_actor(std::string const &definition, vec3d const &position, vec3<math::angle> const &angles);
  void place_actor(scene_handle handle, vec3d const &position, vec3<math::angle> const &angles);
  void show_actor(scene_handle handle, bool visible);
  bool terrain_intact(unsigned int x, unsigned int z);
  bool terrain_destroyed(vec3<int32_t> const &position);
  instance_result collide_terrain(vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t damage = 0, bool player = true, std::function<void(uint16_t)> response = {});
  instance_result collide_actor(scene_handle handle, vec3<int32_t> const &previous, vec3<int32_t> const &current, uint16_t damage, std::function<void(uint16_t)> response = {}, std::function<void(int)> damage_response = {}, bool player = false);
  void apply_actor_contact_damage(scene_handle handle, uint16_t damage);
  bool actor_destroyed(scene_handle handle) const;
  int16_t actor_type(scene_handle handle) const;
  int16_t terrain_type(vec3<int32_t> const &position);
  std::optional<flight::landing_port> terrain_landing_port(vec2<int16_t> const &cell);
  std::optional<flight::landing_port> actor_landing_port(scene_handle handle) const;
  std::vector<vec3<int16_t>> actor_damage_centres(scene_handle handle) const;
  uint16_t actor_impact_damage(scene_handle handle) const;
  void queue_actor(scene_handle handle, vec3d const &position, vec3<math::angle> const &angles);
  void queue_model(std::string const &name, vec3d const &position);
  instance_result actor_event(scene_handle handle, unsigned int entry);
  void prepare_terrain_cell(unsigned int x, unsigned int z);
  instance_result terrain_event(unsigned int x, unsigned int z, unsigned int entry);
  scene_events advance(timer_ticks elapsed);
  void draw(render::software_renderer &renderer, render::camera const &view, unsigned int radius, std::function<void()> const &final_submissions = {}, std::optional<int32_t> camera_anchor_y = {});
};

} // namespace tfx::world
