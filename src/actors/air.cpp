#include "air.h"
#include <algorithm>
#include <bit>
#include <format>
#include <stdexcept>
#include <utility>
#include "math/attitude.h"
#include "world/environment.h"

namespace tfx::actors {
namespace {

unsigned int constexpr controller_budget{1024}, burst_shift{10}, burst_mask{63u << burst_shift};
int constexpr fixed_units_per_foot{32}, fixed_units_per_mile{5280 * fixed_units_per_foot};
int constexpr waypoint_near_radius{world::cell_units * position_unit};
enum class air_action : uint8_t { route, retire_ejected, retire_crashed, falling, normal, finish_takeoff, manoeuvre, engagement, intercept, evasive, escape, waiting, clear };

int32_t wrap(int64_t const value) {
  return std::bit_cast<int32_t>(static_cast<uint32_t>(value));
}
int16_t word(int const value) {
  return math::signed_word(static_cast<uint16_t>(value));
}
int32_t absolute(int32_t const value) {
  return value < 0 ? wrap(-static_cast<int64_t>(value)) : value;
}
bool flagged(air_actor const &actor, air_flag const flag) {
  return (actor.flight.pose.flags & std::to_underlying(flag)) != 0;
}
void set_flag(air_actor &actor, air_flag const flag, bool const enabled = true) {
  if(enabled) actor.flight.pose.flags |= std::to_underlying(flag);
  else actor.flight.pose.flags &= static_cast<uint16_t>(~std::to_underlying(flag));
}
void push(air_actor &actor, air_action const action) {
  if(!(actor.actions >> 24)) actor.actions = (actor.actions << 8) | std::to_underlying(action);
}
int32_t difference(int32_t const a, int32_t const b) {
  return wrap(static_cast<int64_t>(a) - b);
}
int32_t horizontal_distance(vec3<int32_t> const &a, vec3<int32_t> const &b) {
  return std::max(absolute(difference(a.x,b.x)),absolute(difference(a.z,b.z)));
}
math::angle direction(int32_t vertical, int32_t horizontal) {
  while(vertical < -32768 || vertical > 32767 || horizontal < -32768 || horizontal > 32767) { vertical >>= 1; horizontal >>= 1; }
  return math::direction_angle(static_cast<int16_t>(vertical),static_cast<int16_t>(horizontal));
}
vec2<math::angle> direction_to(vec3<int32_t> const &from, vec3<int32_t> const &to) {
  /// Native 0xc9714 uses horizontal Chebyshev distance for pitch, then independently quantises the heading pair.
  return {
    direction(difference(to.y,from.y),horizontal_distance(from,to)),
    direction(difference(to.x,from.x),difference(to.z,from.z)),
  };
}
vec3<int32_t> cell_position(int16_t const x, int16_t const z, int32_t const y) {
  return {
    wrap(static_cast<int64_t>(x) * world::cell_units * position_unit + world::cell_units / 2 * position_unit),
    y,
    wrap(static_cast<int64_t>(z) * world::cell_units * position_unit + world::cell_units / 2 * position_unit),
  };
}
void approach_heading(air_actor &actor, int16_t const error, air_control_context const &context) {
  if(command_turn(actor.flight,actor.performance,error,context)) command_speed(actor.flight,actor.performance,static_cast<int32_t>(cruise_speed(actor.flight,actor.performance,context.turn_envelope)) << speed_fraction_bits);
}

} // anonymous namespace

unsigned int air_registry_index(initial_actor const &actor) {
  if(actor.kind != record_kind::aircraft || actor.slot >= aircraft_per_side) throw std::invalid_argument{"invalid air pool identity"};
  return (actor.side == allegiance::allied ? aircraft_per_side : 0) + actor.slot;
}

air_runtime::air_runtime(program const &program, std::span<initial_actor const> const initial, std::span<profile const> const profiles, std::span<formation_offset const> const offsets, std::span<uint8_t const> const envelope, math::random_state const seed) : formation{offsets}, envelope{envelope}, random{seed} {
  if(formation.size() != aircraft_per_group) throw std::invalid_argument{"missing air formation table"};
  for(auto const &record : program.records) commands.push_back(record.body);
  for(auto const &actor : initial) {
    if(actor.kind != record_kind::aircraft) continue;
    auto const profile{std::ranges::find(profiles,actor.profile_id,&actors::profile::id)};
    if(profile == profiles.end()) throw std::runtime_error{"missing air profile"};
    actors.at(air_registry_index(actor)) = air_actor{
      .flight{
        .pose{actor},
      },
      .performance{decode_air_performance(*profile)},
      .location{
        .record{actor.record},
        .address{0},
      },
    };
  }
}

std::span<std::optional<air_actor> const> air_runtime::aircraft() const {
  return actors;
}

std::span<uint8_t const> air_runtime::program_bytes(unsigned int const record) const {
  return commands.at(record);
}

vec3<int32_t> air_runtime::formation_position(vec3<int32_t> const &position, math::angle const heading, unsigned int const member) const {
  auto result{vec3<int32_t>{position}};
  auto const &offset{formation[member]};
  move(result,{0,heading,0},offset.forward_distance);
  move(result,{0,static_cast<math::angle>(heading + offset.heading),0},offset.distance);
  result.y = wrap(static_cast<int64_t>(result.y) + offset.height);
  return result;
}

void air_runtime::course(air_actor &actor, vec3<int32_t> const &destination, int32_t const distance, bool const pitch, air_control_context const &context) {
  shorten_air_step(actor.flight,distance);
  auto const angles{direction_to(actor.flight.pose.position,destination)};
  if(pitch) command_pitch(actor.flight,actor.performance,static_cast<math::angle>(altitude_pitch(actor.flight,actor.performance,destination.y)),context);
  approach_heading(actor,word(angles.y - actor.flight.pose.angles.y),context);
}

bool air_runtime::follow_formation(air_actor &actor, air_control_context const &context) {
  auto &pose{actor.flight.pose};
  if(pose.leader == 255 || flagged(actor,air_flag::waypoint_steering) || !flagged(actor,air_flag::airborne)) return false;
  auto const pool{pose.side == allegiance::allied ? aircraft_per_side : 0};
  auto const &leader{actors.at(pool + pose.leader)};
  if(!leader || flagged(*leader,air_flag::crashed) || flagged(*leader,air_flag::retired)) { pose.leader = 255; return false; }
  auto const destination{formation_position(leader->flight.pose.position,leader->flight.pose.angles.y,pose.formation)};
  int32_t const distance{std::max(horizontal_distance(pose.position,destination),absolute(difference(destination.y,pose.position.y)))};
  auto const &offset{formation[pose.formation]};
  auto const capture{wrap(static_cast<int64_t>(offset.forward_distance) + offset.distance)};
  if(flagged(actor,air_flag::joining_formation)) {
    if(distance <= capture) {
      set_flag(actor,air_flag::joining_formation,false);
      if(actor.location != leader->location) { actor.location = leader->location; pose.flags |= burst_mask; }
      return false;
    }
  } else {
    if(distance <= wrap(static_cast<int64_t>(capture) * 8)) return false;
    set_flag(actor,air_flag::joining_formation);
  }
  auto const angles{direction_to(pose.position,destination)};
  shorten_air_step(actor.flight,distance);
  command_pitch(actor.flight,actor.performance,angles.x,context);
  int32_t speed{wrap(static_cast<int64_t>(leader->flight.pose.speed) + (static_cast<int64_t>(distance / (100 * fixed_units_per_foot)) << speed_fraction_bits))};
  if(command_turn(actor.flight,actor.performance,word(angles.y - pose.angles.y),context)) speed = static_cast<int32_t>(cruise_speed(actor.flight,actor.performance,envelope)) << speed_fraction_bits;
  command_speed(actor.flight,actor.performance,speed);
  return true;
}

std::vector<air_request> air_runtime::advance(air_context const &context) {
  std::vector<air_request> requests;
  // Original 0x75784 visits the other/hostile air pool, then the allied pool; followers observe their leader's updated state.
  for(unsigned int index{0}; index != actors.size(); ++index) if(actors[index] && !flagged(*actors[index],air_flag::retired)) advance_actor(index,context,requests);
  return requests;
}

void air_runtime::advance_actor(unsigned int const index, air_context const &world, std::vector<air_request> &requests) {
  auto &actor{*actors[index]};
  auto &state{actor.flight};
  auto &pose{state.pose};
  air_control_context const context{
    .model{world.model},
    .turn_envelope{envelope},
  };
  auto const emit{[&](auto data) {
    auto &request{requests.emplace_back()};
    request.actor = index;
    request.data.template emplace<decltype(data)>(std::move(data));
  }};
  auto const visual{[&](unsigned int const entry) { emit(air_scenery_event{.entry{entry}}); }};
  auto const launch{[&](vec3<int32_t> const &target, uint16_t const weapon) {
    int const jitter{std::clamp(static_cast<int>(math::signed_word(random.next())),-182,182)};
    emit(air_weapon{
      .position{vec3<int32_t>{pose.position}},
      .angles{pose.angles.x,static_cast<math::angle>(pose.angles.y + jitter),0},
      .speed{math::signed_word(static_cast<uint16_t>(pose.speed >> speed_fraction_bits))},
      .weapon{weapon},
      .target{vec3<int32_t>{target}},
    });
  }};
  if(state.input_ticks <= 0) {
    bool ready{false};
    for(unsigned int step{0}; step != controller_budget && !ready; ++step) {
      auto const mode{static_cast<air_action>(std::min(actor.actions & 255,12u))};
      if(mode == air_action::clear) { actor.actions = 0; continue; }
      if(mode == air_action::retire_ejected || mode == air_action::retire_crashed) {
        actor.actions = 0;
        set_flag(actor,air_flag::retired);
        return;
      }
      if(mode == air_action::waiting) {
        if(state.input_ticks < 0) { ++state.input_ticks; return; }
        if(actor.wait_seconds > 0) { state.input_ticks = -air_control_horizon; --actor.wait_seconds; return; }
        actor.actions >>= 8;
        continue;
      }
      if(mode == air_action::finish_takeoff) {
        command_pitch(state,actor.performance,0,context);
        actor.actions >>= 8;
        continue;
      }
      if(mode == air_action::normal) {
        actor.actions >>= 8;
        reset_air_controls(state);
        set_flag(actor,air_flag::afterburner,pose.speed >= static_cast<int32_t>(actor.performance.afterburner_speed) << speed_fraction_bits);
        // Target acquisition is an explicit boundary until the live combat controller is connected.
        emit(air_target_scan{});
        if(follow_formation(actor,context)) ready = true;
        continue;
      }
      if(mode != air_action::route) throw std::runtime_error{std::format("aircraft {} (profile {}, record {}, byte {}) needs combat/manoeuvre action {}",index,pose.profile_id,actor.location.record,actor.location.address,std::to_underlying(mode))};
      auto &bytes{commands.at(actor.location.record)};
      resources::binary_view const code{bytes};
      auto const pc{actor.location.address};
      auto const opcode{static_cast<command>(code.byte(pc))};
      auto const operand{[&](unsigned int const n) { return code.le16(pc + 1 + n * 2); }};
      auto const branch{[&](int const amount) {
        int64_t const target{static_cast<int64_t>(actor.location.address) + amount};
        if(target < 0 || static_cast<uint64_t>(target) >= bytes.size()) throw std::runtime_error{"air waypoint branch leaves its program"};
        actor.location.address = static_cast<unsigned int>(target);
      }};
      auto const store{[&](unsigned int const address, int32_t const value) {
        for(unsigned int byte{0}; byte != 4; ++byte) bytes.at(address + byte) = static_cast<uint8_t>(static_cast<uint32_t>(value) >> (byte * 8));
      }};
      auto const destination{[&](unsigned int const first) {
        auto result{cell_position(math::signed_word(operand(first)),math::signed_word(operand(first + 1)),pose.position.y)};
        if(pose.formation) result = formation_position(result,pose.angles.y,pose.formation);
        return result;
      }};
      switch(opcode) {
      case command::end: return;
      case command::aircraft_initial_state: code.slice(pc,25); push(actor,air_action::normal); branch(25); break;
      case command::reserved_7: code.slice(pc,11); branch(11); break;
      case command::reserved_8: code.slice(pc,9); branch(9); break;
      case command::speed:
        command_speed(state,actor.performance,std::bit_cast<int32_t>(static_cast<uint32_t>(operand(0)) << speed_fraction_bits));
        branch(3);
        break;
      case command::altitude:
        // Native 0x77ba0 snaps within 91 angle units and otherwise omits command_pitch's small-error adjustment.
        {
          int32_t const height{wrap(static_cast<int64_t>(formation[pose.formation].height) - static_cast<int64_t>(operand(0)) * fixed_units_per_foot)};
          int16_t const target_pitch{altitude_pitch(state,actor.performance,height)};
          int16_t const error{word(target_pitch - pose.angles.x)};
          if(error != -32768 && std::abs(static_cast<int>(error)) < 91) { state.angular_rate.x = 0; pose.angles.x = static_cast<math::angle>(pose.angles.x + error); }
          else {
            int const maximum{maximum_turn_rate(state,actor.performance,context)};
            state.angular_rate.x = static_cast<int16_t>(std::clamp(error / air_control_horizon,-maximum,maximum));
          }
          if(state.input_ticks > air_control_horizon) state.input_ticks = air_control_horizon;
          branch(3);
        }
        break;
      case command::move_until_near: case command::waypoint_branch:
        {
          push(actor,air_action::normal);
          bool const near_command{opcode == command::move_until_near};
          auto const target{destination(near_command ? 0 : 1)};
          int32_t const distance{horizontal_distance(pose.position,target)};
          bool const near{distance < waypoint_near_radius};
          if(near) pose.flags |= static_cast<uint16_t>(burst_mask | std::to_underlying(air_flag::new_waypoint));
          if(near_command) branch(near ? 7 : -math::signed_word(operand(2)));
          else branch(-math::signed_word(operand(near ? 3 : 0)));
          if(!flagged(actor,air_flag::waypoint_steering)) {
            if(!near_command || !near) course(actor,target,distance,false,context);
          }
          ready = !near_command || !near || flagged(actor,air_flag::waypoint_steering);
        }
        break;
      case command::pursue_waypoint:
        {
          set_flag(actor,air_flag::waypoint_steering);
          auto const target{destination(1)};
          int32_t const distance{horizontal_distance(pose.position,target)};
          if(distance > static_cast<int32_t>(operand(0)) * fixed_units_per_mile) course(actor,target,distance,true,context);
          branch(7);
        }
        break;
      case command::wait:
        if(flagged(actor,air_flag::awaiting_takeoff)) {
          set_flag(actor,air_flag::awaiting_takeoff,false);
          actor.wait_seconds = word(math::signed_word(operand(0)) * 60 + math::signed_word(operand(1)));
          push(actor,air_action::waiting);
        }
        branch(5);
        break;
      case command::radio_message:
        if(!operand(0)) {
          auto const text{code.slice(pc + 3,40)};
          auto const end{std::ranges::find(text,uint8_t{0})};
          emit(air_radio{.text{text.begin(),end}});
          bytes.at(pc + 1) = 1;
          bytes.at(pc + 2) = 0;
        }
        branch(43);
        break;
      case command::takeoff:
        if(flagged(actor,air_flag::airborne)) { branch(7); break; }
        if(!pose.speed) {
          pose.angles = vec3<math::angle>{0,static_cast<math::angle>(operand(0) * 182),0};
          state.acceleration = std::bit_cast<int32_t>(static_cast<uint32_t>(operand(1)) << speed_fraction_bits) / air_control_horizon;
          state.acceleration |= 1;
          set_flag(actor,air_flag::afterburner);
        }
        if(pose.speed >= std::bit_cast<int32_t>(static_cast<uint32_t>(operand(2)) << speed_fraction_bits)) {
          state.angular_rate.x = -18;
          state.input_ticks = air_control_horizon;
          branch(7);
          set_flag(actor,air_flag::airborne);
          push(actor,air_action::finish_takeoff);
          push(actor,air_action::normal);
        } else {
          if(!state.acceleration) throw std::runtime_error{"air takeoff has zero acceleration"};
          int const ticks{difference(std::bit_cast<int32_t>(static_cast<uint32_t>(operand(2)) << speed_fraction_bits),pose.speed) / state.acceleration};
          state.input_ticks = static_cast<int16_t>(ticks < 1 || ticks > air_control_horizon ? air_control_horizon : ticks);
        }
        ready = true;
        break;
      case command::attack_ground:
        if(flagged(actor,air_flag::new_waypoint)) {
          set_flag(actor,air_flag::new_waypoint,false);
          vec2<int16_t> const cell{math::signed_word(operand(0)),math::signed_word(operand(1))};
          if(world.intact_ground_target && world.intact_ground_target(cell)) {
            auto const target{cell_position(cell.x,cell.y,0)};
            store(pc + 5,target.x); store(pc + 9,target.y); store(pc + 13,target.z);
            // This opcode launches without dispersion; its release angles and target are explicit outputs.
            emit(air_weapon{
              .position{vec3<int32_t>{pose.position}},
              .angles{pose.angles.x,pose.angles.y,0},
              .speed{math::signed_word(static_cast<uint16_t>(pose.speed >> speed_fraction_bits))},
              .weapon{operand(8)},
              .target{vec3<int32_t>{target}},
            });
          }
        }
        branch(19);
        break;
      case command::conditional_action:
        {
          vec2<int16_t> const cell{math::signed_word(operand(0)),math::signed_word(operand(1))};
          if(world.intact_ground_target && world.intact_ground_target(cell)) {
            auto const target{cell_position(cell.x,cell.y,0)};
            store(pc + 5,target.x); store(pc + 9,target.y); store(pc + 13,target.z);
            if(horizontal_distance(pose.position,target) < fixed_units_per_mile) {
              auto const heading{math::signed_word(direction_to(pose.position,target).y)};
              if(heading > -16383 && heading < 16383) launch(target,8);
            }
          }
          branch(17);
        }
        break;
      case command::conditional_action_12:
        {
          unsigned int remaining{static_cast<unsigned int>(pose.flags) >> burst_shift};
          if(remaining == 63) {
            remaining = std::min<unsigned int>(operand(3),62);
            if(remaining && code.byte(pc + 11)) visual(code.byte(pc + 11));
            pose.flags = static_cast<uint16_t>((pose.flags & ~burst_mask) | (remaining << burst_shift));
          }
          if(remaining) {
            auto const target{cell_position(math::signed_word(operand(0)),math::signed_word(operand(1)),0)};
            store(pc + 13,target.x); store(pc + 17,target.y); store(pc + 21,target.z);
            if(horizontal_distance(pose.position,target) < static_cast<int32_t>(operand(4)) * fixed_units_per_foot) {
              auto const heading{math::signed_word(direction_to(pose.position,target).y)};
              if(heading > -16383 && heading < 16383) {
                launch(target,operand(2));
                --remaining;
                pose.flags = static_cast<uint16_t>((pose.flags & ~burst_mask) | (remaining << burst_shift));
                if(!remaining && code.byte(pc + 12)) visual(code.byte(pc + 12));
              }
            }
          }
          branch(25);
        }
        break;
      default: return;
      }
    }
    if(!ready) throw std::runtime_error{"air route does not yield within its instruction budget"};
  }
  if(auto const event{advance_air_motion(state)}) visual(std::to_underlying(*event));
}

} // namespace tfx::actors
