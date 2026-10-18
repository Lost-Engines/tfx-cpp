#include "gear_controls.h"

namespace tfx::flight {

gear_key_effects press_gear_key(gear_key_context const &context) {
  gear_key_effects result;
  if(context.aircraft == player_aircraft::eurofighter && !context.gear_down &&
      context.speed > eurofighter_maximum_gear_speed && !context.automatic_landing) {
    result.speed_warning = true;
    return result;
  }
  if(context.inhibited || context.crashed || context.disabled || context.automatic_landing || context.landed ||
      context.condition == system_condition::failed) return result;
  result.gear_down = !context.gear_down;
  return result;
}

} // namespace tfx::flight
