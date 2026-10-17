#pragma once

#include "models/shape.h"
#include "render/camera.h"

namespace tfx::render {

// Project a flat model face through native Q16 projection and integer screen
// clipping, including native near-plane crossings. Returns false for inspection
// cameras, out-of-range coordinates or the separate far-plane path; no pixels
// are changed in that case.
bool integer_model_polygon(framebuffer &output, std::span<models::model_vertex const> vertices, camera const &view, uint8_t colour);

// Original opcode-21 branch and polygon winding are distinct tests. Null means
// the supplied camera/coordinates do not have a native projection here.
std::optional<bool> model_facing(std::span<models::model_vertex const> vertices, camera const &view, models::facing_test purpose);

} // namespace tfx::render
