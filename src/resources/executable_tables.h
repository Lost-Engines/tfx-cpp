#pragma once

#include <filesystem>
#include <span>
#include <vector>
#include "resources/binary.h"

namespace tfx::resources {

class executable_tables {
private:
  std::vector<bytes> circles;

public:
  executable_tables(std::filesystem::path const &path);
  std::span<uint8_t const> circle(unsigned int radius) const;
};

} // namespace tfx::resources
