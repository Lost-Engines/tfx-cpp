#include "executable_tables.h"
#include <stdexcept>

namespace tfx::resources {

executable_tables::executable_tables(std::filesystem::path const &path) {
  /// Read original circle spans as data; no original instructions execute at runtime
  auto const source{read_file(path)};
  uint64_t checksum{14695981039346656037ull};
  for(auto const byte : source) checksum = (checksum ^ byte) * 1099511628211ull;
  if(source.size() != 1032503 || checksum != 0xcc1e305ba7e177f0ull) throw std::runtime_error{"this reconstruction currently requires the September 1994 TFX 2.05 executable (TFX.DAT)"};
  binary_view const view{source};
  unsigned int constexpr circle_base{0x70aa4 + 0x65a84}, circle_limit_field{0x70aa4 + 0x66ea0};
  auto const limit{view.le16(circle_limit_field)};
  circles.resize(limit);
  for(unsigned int radius{1}; radius != limit; ++radius) {
    auto const spans{view.slice(circle_base + view.le16(circle_base + (radius - 1) * 2), radius)};
    circles[radius].assign(spans.begin(), spans.end());
  }
}

std::span<uint8_t const> executable_tables::circle(unsigned int const radius) const {
  /// The native constructor rejects zero and radii at or beyond its table limit
  if(radius >= circles.size()) return {};
  return circles[radius];
}

} // namespace tfx::resources
