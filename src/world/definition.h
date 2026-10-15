#pragma once

#include <array>
#include <cstdint>
#include <span>
#include <string>
#include <vector>
#include "math/native.h"

namespace tfx::world {

unsigned int constexpr part_parameters{8};
struct model_part {
  std::string name;
  vec3<math::angle> rotation;
  std::array<uint8_t, part_parameters> parameters{0};
};
struct part_draw {
  unsigned int slot;
  vec3d anchor;
};
struct parameter_stream {
  unsigned int part;
  unsigned int parameter;
  std::vector<uint16_t> words;
};
struct definition {
  std::vector<model_part> parts;
  std::vector<part_draw> draws;
  std::vector<parameter_stream> streams;
  uint16_t flags;
  definition(std::span<uint8_t const> source, std::span<std::string const> names);
};

std::vector<std::string> model_names(std::span<uint8_t const> source);

} // namespace tfx::world
