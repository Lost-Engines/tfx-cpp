#pragma once

#include <span>
#include "resources/binary.h"

namespace tfx::resources {

size_t constexpr maximum_resource_size{256 * 1024 * 1024};
bool is_ra(std::span<uint8_t const> source);
bytes decode_ra(std::span<uint8_t const> source, size_t maximum_size = maximum_resource_size);

} // namespace tfx::resources
