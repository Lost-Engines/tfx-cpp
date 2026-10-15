#pragma once

#include <array>
#include <functional>
#include <map>
#include <optional>
#include <set>
#include <span>
#include <string>
#include <vector>
#include "math/native.h"
#include "resources/binary.h"

namespace tfx::models {

// Values are the original disk opcodes; no rewritten native function pointers
// are needed to retain the instruction addresses and relative branches
struct shape_instruction {
  unsigned int address;
  uint16_t opcode;
  std::vector<uint16_t> operands;
};
struct shape_detail {
  unsigned int distance;
  unsigned int kind;
  unsigned int offset;
};
struct shape {
  std::map<unsigned int, shape_instruction> instructions;
  std::vector<unsigned int> levels;
  std::vector<shape_detail> details;
  std::string texture_name;
  int16_t sort_depth_bias;
  shape(std::span<uint8_t const> source);
};

enum class primitive_kind : uint32_t { polygon, line, point };
enum class texture_source { global, model };
struct texture_binding {
  texture_source source;
  unsigned int slot;
  std::string name;
};
struct model_vertex {
  vec3d position;
  vec2d uv;
  double shade{-1};
};
struct primitive {
  primitive_kind kind;
  std::vector<model_vertex> vertices;
  unsigned int colour;
  int mode{-1};
  std::optional<texture_binding> texture{std::nullopt};
  double radius{0};
  unsigned int pixel_size{0};
  bool rounded{false};
  unsigned int source_address{0};
};
struct shape_context {
  std::array<uint8_t, 256> parameters{0};
  uint16_t status{0};
  int16_t distance{0};
  unsigned int level{0};
  uint8_t initial_state{0};
  double reference_scale{1};
  bool facing{true};
  std::function<vec2d(vec3d const&)> project;
  math::random_state *jitter{nullptr};
};
struct shape_geometry {
  std::vector<primitive> primitives;
  std::set<std::string> warnings;
  unsigned int steps{0};
};

bool condition(uint16_t opcode, uint16_t operand, uint8_t state, int16_t distance, uint16_t status);
shape_geometry interpret(shape const &program, shape_context const &context);

} // namespace tfx::models
