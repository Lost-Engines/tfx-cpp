#include "runtime.h"
#include <stdexcept>
#include <utility>

namespace tfx::weapons {

runtime::runtime(std::span<definition const> const weapons, runtime_callbacks handlers, unsigned int const capacity) : definitions{weapons}, callbacks{std::move(handlers)}, slots(capacity) {
  if(!capacity || !callbacks.motion_inputs) throw std::invalid_argument{"projectile runtime needs a pool and motion inputs"};
  free.reserve(capacity);
  for(auto &slot : slots) free.push_back(&slot);
}

void runtime::retire(pool_slot &slot) {
  auto const &shot{slot.value};
  if(shot.state.weapon == std::to_underlying(weapon_id::chaff) || shot.state.weapon == std::to_underlying(weapon_id::flare)) {
    for(auto *other{first}; other; other = other->next) if(other->value.target.projectile == shot.id) {
      other->value.state.motion = flight_stage::coasting;
      other->value.state.ticks = 30000;
    }
  }
  if(callbacks.target_cleared) callbacks.target_cleared(shot);
  if(callbacks.reset_visual) callbacks.reset_visual(shot.state.weapon,shot.state.secondary);
  if(slot.previous) slot.previous->next = slot.next;
  else first = slot.next;
  if(slot.next) slot.next->previous = slot.previous;
  else last = slot.previous;
  active.erase(shot.id);
  free.push_back(&slot);
}

projectile_id runtime::launch(release const &request) {
  if(request.weapon >= definitions.size()) throw std::runtime_error{"projectile weapon index exceeds the original table"};
  if(!next_id) throw std::runtime_error{"projectile identity space exhausted"};
  if(free.empty()) retire(*last);
  auto &slot{*free.back()};
  free.pop_back();
  // Keep the record's address stable: a dispenser can recycle its own record during its callback.
  projectile_id const id{next_id++};
  slot.value = active_projectile{
    .id{id},
    .state{weapons::launch(definitions[request.weapon],static_cast<uint8_t>(request.weapon),request.position,request.angles,request.speed)},
    .owner{request.owner},
    .target{request.target},
    .mount{request.mount},
  };
  slot.previous = nullptr;
  slot.next = first;
  if(first) first->previous = &slot;
  else last = &slot;
  first = &slot;
  active.emplace(id,&slot.value);
  if(callbacks.reset_visual) callbacks.reset_visual(request.weapon,false);
  if(callbacks.launched) callbacks.launched(slot.value);
  return id;
}

projectile_id runtime::countermeasure(actor_identity const owner, vec3<int32_t> const &position, bool const radar, int16_t const strength, math::random_state &random) {
  auto const decoy{launch({
    .weapon{std::to_underlying(radar ? weapon_id::chaff : weapon_id::flare)},
    .position{vec3<int32_t>{position}},
    .angles{0,0,0},
    .speed{0},
    .owner{owner},
    .target{},
  })};
  // Native 0xa35d0 visits newest first and consumes a random value even for a nonpositive signed strength.
  for(auto *slot{first}; slot; slot = slot->next) {
    auto &shot{slot->value};
    if(shot.target.actor != owner) continue;
    uint8_t const category{definitions[shot.state.weapon].category};
    if(category != static_cast<unsigned int>(radar) && category != 2) continue;
    if(static_cast<int>(random.next() & 127) >= strength) continue;
    if(callbacks.target_cleared) callbacks.target_cleared(shot);
    shot.target.actor.reset();
    shot.target.projectile = decoy;
    shot.target.position = position;
  }
  return decoy;
}

std::map<projectile_id,active_projectile const*> const &runtime::projectiles() const {
  return active;
}

void runtime::advance(simulation::timer_ticks const elapsed, math::random_state &random, bool const ground_effects) {
  simulation::projectile_clock clock{elapsed};
  while(auto const ticks{clock.next()}) {
    auto *slot{first};
    unsigned int budget{static_cast<unsigned int>(slots.size()) * 4096u};
    while(slot) {
      if(!budget--) throw std::runtime_error{"projectile recycling does not yield within its update budget"};
      // The original saves the next record before calling motion. It may be recycled and reinserted by a child launch.
      auto *const next{slot->next};
      auto &shot{slot->value};
      if(shot.spent || !shot.state.ticks) retire(*slot);
      else {
        auto context{callbacks.motion_inputs(shot,*ticks)};
        context.elapsed = *ticks;
        context.target = shot.target.actor ? callbacks.actor_position(*shot.target.actor) : vec3<int32_t>{shot.target.position};
        if(shot.target.projectile) {
          auto const found{active.find(*shot.target.projectile)};
          if(found != active.end()) context.target = found->second->state.position;
        }
        auto const result{advance_motion(shot.state,definitions[shot.state.weapon],context,random,{
          .release{[&](child_release const &child) {
            launch({
              .weapon{child.weapon},
              .position{vec3<int32_t>{child.position}},
              .angles{vec3<math::angle>{child.angles}},
              .speed{child.speed},
              .owner{shot.owner},
              .target{},
            });
          }},
          .current_definition{[&](uint8_t const weapon)->definition const& { return definitions[weapon]; }},
        })};
        if(result.reset_visual && callbacks.reset_visual) callbacks.reset_visual(shot.state.weapon,shot.state.secondary);
        if(ground_effects && shot.state.position.y >= 0) {
          if(callbacks.ground_impact) callbacks.ground_impact(shot);
          shot.spent = true;
        }
      }
      slot = next;
    }
    // Contact traversal starts afresh, so births participate even before their ordinary first motion update.
    if(callbacks.contacts) for(auto *contact{first}; contact; contact = contact->next) callbacks.contacts(contact->value,*ticks);
  }
}

} // namespace tfx::weapons
