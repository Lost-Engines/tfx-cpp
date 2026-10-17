#pragma once

#include <cstdint>
#include <span>

namespace tfx::audio {

class midi_receiver {
public:
  virtual ~midi_receiver() = default;
  virtual void short_message(uint32_t packed) = 0;
  virtual void sysex(std::span<uint8_t const> message) = 0;
  virtual void render(std::span<float> stereo) = 0;
};

} // namespace tfx::audio
