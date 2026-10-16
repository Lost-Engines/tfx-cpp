#pragma once

#include <filesystem>
#include <array>
#include <span>
#include <vector>
#include "resources/binary.h"
#include "actors/program.h"
#include "actors/air_motion.h"
#include "weapons/definition.h"
#include "weapons/loadout.h"

namespace tfx::resources {

struct hud_glyph {
  unsigned int advance;
  std::array<uint8_t,6> rows;
};

class executable_tables {
private:
  std::vector<bytes> circles;
  std::array<uint8_t,64> character_map;
  std::array<hud_glyph,51> glyphs;

public:
  std::vector<weapons::definition> weapons;
  weapons::arming_tables arming;
  std::string timer_expired_message;
  std::array<vec3<int16_t>,2> cannon_mounts;
  std::array<std::array<vec3<int16_t>,10>,3> store_mounts;
  std::array<actors::formation_offset,actors::aircraft_per_group> formations;
  std::array<uint8_t,actors::envelope_bytes> aircraft_envelopes;
  executable_tables(std::filesystem::path const &path);
  std::span<uint8_t const> circle(unsigned int radius) const;
  hud_glyph const *glyph(unsigned char character) const;
};

} // namespace tfx::resources
