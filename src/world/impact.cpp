#include "impact.h"

namespace tfx::world {

impact_surface classify_impact(render::framebuffer const &frame, std::optional<vec2<int16_t>> const &point, bool const water_world) {
  // Native 0x7da20 deliberately classifies a pixel from the rendered image, rather than querying collision geometry.
  if(!point || point->x <= 0 || point->x >= render::screen_width || point->y <= 0 || point->y >= render::screen_height) return impact_surface::unknown;
  auto const pixel{frame.pixels[static_cast<unsigned int>(point->y * render::screen_width + point->x)]};
  impact_surface surface{impact_surface::unknown};
  if((pixel >= 0xb0 && pixel <= 0xdf) || (pixel >= 0x90 && pixel <= 0x9f)) surface = impact_surface::terrain;
  if(pixel >= 0x70 && pixel <= 0x7f) surface = impact_surface::water;
  if((pixel >= 0xa0 && pixel <= 0xaf) || (pixel >= 0x20 && pixel <= 0x2f) || (pixel >= 0xe0 && pixel <= 0xf0)) surface = impact_surface::structure;
  if(water_world && surface != impact_surface::unknown) surface = impact_surface::water;
  return surface;
}

crash_appearance select_crash_appearance(int16_t const collision, std::optional<int16_t> const terrain_type, impact_surface const sampled_surface, bool const water_world) {
  // Native 0x7d48a..0x7d4e9: collision 2 bypasses even the forced-water choice.
  int16_t constexpr land_collision{2}, sea_definition_type{1};
  if(collision != land_collision && ((terrain_type && *terrain_type == sea_definition_type) || sampled_surface == impact_surface::water || water_world)) return crash_appearance::water;
  return crash_appearance::land;
}

} // namespace tfx::world
