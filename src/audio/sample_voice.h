#pragma once

#include <mutex>
#include "audio/sample_bank.h"

namespace tfx::audio {

// Device-independent single-stream DAC. The bank must outlive playback.
// Host requests and the device callback share this small, bounded lock.
class sample_voice {
private:
  sample_bank const &bank;
  sample_scheduler scheduler;
  std::mutex mutex;
  std::vector<unsigned int> queue;
  unsigned int item{0}, offset{0};
  uint64_t phase{0};
  uint32_t const output_rate;

public:
  explicit sample_voice(sample_bank const &bank, uint32_t output_rate);
  void enable(bool enabled);
  void advance(simulation::timer_ticks elapsed);
  void submit(sample_priority priority, std::span<unsigned int const> sequence);
  // Add dual-mono PCM, preserving DMA sample holds and fractional boundaries
  // across callbacks. No interpolation, normalisation or invented spatialisation.
  void render(std::span<float> stereo);
  sample_scheduler_state state();
};

} // namespace tfx::audio
