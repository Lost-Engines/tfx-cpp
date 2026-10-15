#pragma once

#include <map>
#include <set>
#include <string>
#include "render/software_renderer.h"
#include "world/animation.h"
#include "world/assets.h"
#include "world/environment.h"

namespace tfx::world {

struct scene_handle { unsigned int value; };

class scene {
private:
  environment const &terrain;
  assets &resources;
  struct stream_playback {
    unsigned int part;
    unsigned int parameter;
    parameter_player player;
    bool paused{false};
  };
  struct scenery_instance {
    std::vector<model_part> parts;
    std::vector<stream_playback> streams;
    bool all_parameters;
    scenery_instance(definition const &source);
  };
  std::map<unsigned int, scenery_instance> instances;
  struct moving_instance {
    definition const *source;
    scenery_instance state;
    vec3d position;
    mat3d rotation;
  };
  std::map<unsigned int,moving_instance> actors;
  unsigned int next_actor{0};
  void advance_instance(scenery_instance &instance);
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
  void advance(timer_ticks elapsed);
  void draw(render::software_renderer &renderer, render::camera const &view, unsigned int radius);
};

} // namespace tfx::world
