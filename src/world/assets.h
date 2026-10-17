#pragma once

#include <map>
#include <string>
#include <vector>
#include "models/shape.h"
#include "render/colour_remap.h"
#include "resources/archive.h"
#include "world/definition.h"

namespace tfx::world {

class assets {
private:
  resources::archive const &game;
  std::shared_ptr<std::vector<std::string> const> names;
  render::colour_maps colours;
  std::map<std::string, models::shape> shapes;
  std::map<std::string, definition> definitions;
  std::map<std::string, resources::bytes> textures;

public:
  assets(resources::archive const &game);
  render::colour_map const &model_colours(uint8_t row) const;
  models::shape const &shape(std::string const &name);
  definition const &object(std::string const &name);
  std::span<uint8_t const> texture(models::texture_binding const &binding);
};

} // namespace tfx::world
