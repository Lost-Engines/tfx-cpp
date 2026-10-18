#pragma once

#include <cstdint>
#include <optional>
#include <span>
#include <vector>

namespace tfx::audio {

class gus_sample_ram {
private:
  uint32_t next_address{streaming_bytes};
  uint32_t free_bytes;

public:
  static uint32_t constexpr streaming_bytes{32 * 1024};
  explicit gus_sample_ram(unsigned int ram_kib);
  std::optional<uint32_t> allocate(uint32_t bytes);
  uint32_t remaining() const;
};
struct gus_residency {
  std::vector<std::optional<uint32_t>> addresses;
  uint32_t remaining;
};

// Native C52D0/C4F5C try every nonempty sample in their size-sorted order.
// Failed large requests do not prevent later, smaller samples from fitting.
gus_residency plan_gus_residency(std::span<uint32_t const> sample_sizes, unsigned int ram_kib);

} // namespace tfx::audio
