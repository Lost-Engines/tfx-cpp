#pragma once

#include <cstdint>
#include <functional>

namespace tfx::audio {

using midi_byte_sink = std::function<void(uint8_t)>;

} // namespace tfx::audio
