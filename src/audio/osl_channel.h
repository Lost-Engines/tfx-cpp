#pragma once

#include "audio/osl_resource.h"

namespace tfx::audio {

// Native 21-byte OSL channel state, expressed as fields rather than byte slots.
// Device drivers share the bend/note/output caches with the sequencer effects.
struct osl_channel {
  uint8_t allocation{0};
  osl_cell cell{};
  uint16_t pitch_bend{0};
  uint16_t portamento_target{0};
  uint8_t portamento_increasing{0};
  uint8_t portamento_step{0};
  uint8_t arpeggio_counter{0};
  uint8_t arpeggio_note{0};
  uint8_t previous_note{0};
  uint8_t volume{0};
  uint8_t sent_volume{255};
  uint8_t sent_instrument{255};
};

} // namespace tfx::audio
