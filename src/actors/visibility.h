#pragma once

#include "actors/program.h"

namespace tfx::actors {

int32_t constexpr actor_draw_range{16384};
// Original moving-actor admission precedes the renderer's sphere/detail tests.
// Both inputs are Q8 world positions; only surface units test the vertical axis.
bool aircraft_in_draw_region(vec3<int32_t> const &position, vec3<int32_t> const &reference);
bool surface_in_draw_region(vec3<int32_t> const &position, vec3<int32_t> const &reference);

} // namespace tfx::actors
