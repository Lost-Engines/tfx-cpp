#pragma once

#include <optional>
#include "render/framebuffer.h"

namespace tfx::world {

enum class impact_surface : int16_t { unknown = -1, terrain, structure, water };
enum class crash_appearance { land, water };

impact_surface classify_impact(render::framebuffer const &frame, std::optional<vec2<int16_t>> const &point, bool water_world);
crash_appearance select_crash_appearance(int16_t collision, std::optional<int16_t> terrain_type, impact_surface sampled_surface, bool water_world);

} // namespace tfx::world
