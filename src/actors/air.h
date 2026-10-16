#pragma once

#include <array>
#include <functional>
#include <optional>
#include <variant>
#include "actors/air_motion.h"

namespace tfx::actors {

struct air_location {
  unsigned int record;
  unsigned int address;
  bool operator==(air_location const&) const = default;
};
struct air_actor {
  air_state flight;
  air_performance performance;
  air_location location;
  uint32_t actions{0};
  int16_t wait_seconds{0};
};
struct air_target_scan {};
struct air_scenery_event { unsigned int entry; };
struct air_radio { std::string text; };
struct air_weapon {
  vec3<int32_t> position;
  vec3<math::angle> angles;
  int16_t speed;
  uint16_t weapon;
  vec3<int32_t> target;
};
struct air_impact {
  vec3<int32_t> position;
  unsigned int kind;
};
using air_request_data = std::variant<air_target_scan,air_scenery_event,air_radio,air_weapon,air_impact>;
struct air_request {
  unsigned int actor;
  air_request_data data;
};
struct air_context {
  simulation::flight_model model{simulation::flight_model::arcade};
  std::function<bool(vec2<int16_t> const&)> intact_ground_target{};
  std::function<unsigned int(vec3<int32_t> const&)> impact_effect{};
};

unsigned int air_registry_index(initial_actor const &actor);

class air_runtime {
private:
  std::vector<resources::bytes> commands;
  std::array<std::optional<air_actor>,aircraft_per_side * 2> actors;
  std::span<formation_offset const> formation;
  std::span<uint8_t const> envelope;
  math::random_state random;
  void course(air_actor &actor, vec3<int32_t> const &destination, int32_t distance, bool pitch, air_control_context const &context);
  bool follow_formation(air_actor &actor, air_control_context const &context);
  vec3<int32_t> formation_position(vec3<int32_t> const &position, math::angle heading, unsigned int member) const;
  void advance_actor(unsigned int index, air_context const &context, std::vector<air_request> &requests);

public:
  air_runtime(program const &program, std::span<initial_actor const> initial, std::span<profile const> profiles, std::span<formation_offset const> formation, std::span<uint8_t const> envelope, math::random_state random = {});
  std::span<std::optional<air_actor> const> aircraft() const;
  std::span<uint8_t const> program_bytes(unsigned int record) const;
  std::vector<air_request> advance(air_context const &context = {});
};

} // namespace tfx::actors
