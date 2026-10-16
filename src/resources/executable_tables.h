#pragma once

#include <filesystem>
#include <memory>
#include "presentation/fonts.h"
#include "presentation/widget_font.h"
#include "resources/compiled_panel.h"
#include "presentation/pilots.h"
#include "presentation/scores.h"
#include "presentation/cursor.h"
#include "presentation/timing.h"
#include <array>
#include <span>
#include <vector>
#include "resources/binary.h"
#include "actors/program.h"
#include "actors/air_motion.h"
#include "weapons/definition.h"
#include "weapons/loadout.h"
#include "flight/airframes.h"
#include "presentation/arming_assets.h"

namespace tfx::resources {

struct hud_glyph {
  unsigned int advance;
  std::array<uint8_t,6> rows;
};

class executable_tables {
private:
  std::vector<bytes> circles;
  std::unique_ptr<presentation::fonts const> font_data;
  std::unique_ptr<presentation::widget_font const> widget_font_data;
  std::unique_ptr<planner_artwork const> planner_art_data;
  std::unique_ptr<presentation::pilot_assets const> pilot_assets;
  std::unique_ptr<presentation::score_assets const> score_data;
  std::unique_ptr<presentation::arming_assets const> arming_data;
  std::array<uint8_t,64> character_map;
  std::array<hud_glyph,51> glyphs;

public:
  std::vector<weapons::definition> weapons;
  weapons::arming_tables arming;
  std::array<flight::airframe,3> airframes;
  std::string timer_expired_message;
  presentation::dac_palette text_palette;
  std::array<presentation::pointer_style,2> pointers;
  std::vector<int16_t> ship_target_types;
  std::array<vec3<int16_t>,2> cannon_mounts;
  std::array<std::array<vec3<int16_t>,10>,3> store_mounts;
  std::array<actors::formation_offset,actors::aircraft_per_group> formations;
  std::array<uint8_t,actors::envelope_bytes> aircraft_envelopes;
  executable_tables(std::filesystem::path const &path);
  presentation::fonts const &presentation_fonts() const;
  presentation::widget_font const &interface_font() const;
  planner_artwork const &planner_art() const;
  presentation::pilot_assets const &pilots() const;
  presentation::score_assets const &scores() const;
  presentation::arming_assets const &arming_art() const;
  std::span<uint8_t const> circle(unsigned int radius) const;
  hud_glyph const *glyph(unsigned char character) const;
};

} // namespace tfx::resources
