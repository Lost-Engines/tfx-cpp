#pragma once

#include <functional>
#include "math/native.h"
#include "simulation/timing.h"

namespace tfx::flight {

// Slots without an established gameplay label retain their native number rather than an invented purpose.
enum class aircraft_system : unsigned int { gun, fire_control, left_engine, slot_3, wheel_brakes, right_engine, radar, air_brake, ecm, weapons, landing_gear, slot_11 };
enum class system_condition : uint8_t { unavailable, active, normal, failed = 11, intermittent = 14 };
unsigned int constexpr aircraft_system_count{12};
struct damage_state {
  std::array<system_condition,aircraft_system_count> systems;
  std::array<uint16_t,aircraft_system_count> repair_ticks{};
  double accumulated{0};
  int16_t warning{0};
  damage_state();
  system_condition condition(aircraft_system system) const;
};
void apply_damage(damage_state &state, int32_t severity, math::random_state &random, bool invulnerable = false, std::function<void()> const &notify = {});
void repair_systems(damage_state &state, simulation::timer_ticks elapsed);

} // namespace tfx::flight
