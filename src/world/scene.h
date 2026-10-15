#pragma once

#include <set>
#include <string>
#include "render/software_renderer.h"
#include "world/assets.h"
#include "world/environment.h"

namespace tfx::world {

class scene {
private:
  environment const &terrain;
  assets &resources;

public:
  std::set<std::string> warnings;
  unsigned int parts_drawn{0};
  unsigned int primitives_drawn{0};
  scene(environment const &terrain, assets &resources);
  void draw(render::software_renderer &renderer, render::camera const &view, unsigned int radius);
};

} // namespace tfx::world
