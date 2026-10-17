#pragma once

#include "platform/window.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "world/scene.h"

namespace tfx::platform {

// Original 7B2F4: WNN/press-room introduction followed by recorded model
// queues. Reuse the actual flight's renderer, attachments and animation gate.
void replay_recording(window &window, resources::archive const &game,
  resources::executable_tables const &tables, world::scene &scene,
  render::software_renderer &renderer, std::filesystem::path const &path,
  int16_t camera_y, int16_t ground_phase, render::dac_palette const &infrared);

} // namespace tfx::platform
