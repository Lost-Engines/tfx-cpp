#pragma once

#include "platform/window.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "weapons/loadout.h"

namespace tfx::platform {

bool arm_mission(window &window, resources::archive const &game, resources::executable_tables const &tables,
  weapons::armament &inventory, flight::player_aircraft aircraft, unsigned int default_fit);

} // namespace tfx::platform
