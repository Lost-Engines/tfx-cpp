#pragma once

#include <array>
#include <string>
#include <vector>
#include "math/native.h"
#include "resources/archive.h"

namespace tfx::world {

unsigned int constexpr map_width{200}, map_height{200};
int constexpr cell_units{2048};
uint16_t constexpr night_status{1u << 7};

struct terrain_tile {
  math::angle rotation;
  std::vector<std::string> variants;
};
struct mission {
  std::string name;
  std::string environment;
  std::string waypoints;
  vec3d start;
  unsigned int aircraft{0};
  std::string script;
  mission(resources::archive const &game, std::string const &name);
};

class environment {
private:
  std::array<uint16_t, map_width * map_height> cells;
  std::array<uint16_t, map_width * map_height> choices;

public:
  std::string name;
  std::string config;
  std::string palette_name;
  uint16_t status{0};
  std::vector<terrain_tile> tiles;

  environment(resources::archive const &game, std::string name);
  terrain_tile const &tile(unsigned int x, unsigned int z) const;
  std::string const &variant(unsigned int x, unsigned int z) const;
  unsigned int tile_id(unsigned int x, unsigned int z) const;
};

} // namespace tfx::world
