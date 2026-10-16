#pragma once

#include <array>
#include <functional>
#include <optional>
#include "world/animation.h"
#include "world/collision.h"
#include "world/definition.h"

namespace tfx::world {

struct instance_context {
  collision_segment movement{};
  bool player_query{false};
  bool surface_enabled{true};
  uint16_t impact_damage{0};
  uint16_t status{0};
  int16_t distance{0};
  std::function<int16_t(vec3d const&)> anchor_distance{};
  std::function<void(uint16_t)> collision_response{};
  std::function<void(int)> damage_response{};
};
struct scene_request {
  unsigned int opcode;
  std::vector<uint16_t> arguments;
};
struct instance_result {
  std::vector<part_draw> draws;
  std::vector<scene_request> requests;
  unsigned int collisions{0};
  bool volume_hit{false};
  bool marked{false};
  bool surface_present{false};
  int16_t surface_height{0};
  int16_t zone{-1};
  int16_t player_zone{0};
  uint16_t message{0};
  std::vector<int> damage_reports;
};
struct part_stream {
  unsigned int source;
  parameter_player player;
};

class instance {
private:
  definition const &source;
  std::vector<std::array<std::optional<part_stream>,part_parameters>> streams;
  void interpret(unsigned int address, instance_context &context, instance_result &result, unsigned int &budget, unsigned int depth, bool &install_streams);

public:
  std::vector<model_part> parts;
  std::vector<uint16_t> custom;
  bool destroyed{false};
  bool modified{false};
  uint8_t category{0};
  uint16_t impact_damage{0};
  uint16_t health{0};

  explicit instance(definition const &source);
  void apply_contact_damage(uint16_t damage);
  int16_t type() const;
  instance_result execute(unsigned int entry, instance_context const &context = {});
  instance_result animate(instance_context const &context = {});
  std::optional<unsigned int> stream_cursor(unsigned int part, unsigned int parameter) const;
};

} // namespace tfx::world
