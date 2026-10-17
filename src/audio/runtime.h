#pragma once

#include <initializer_list>
#include "audio/sample_voice.h"

namespace tfx::audio {

enum class sample_id : unsigned int {
  gear = 1,
  afterburner_stop = 8,
  ejection = 20,
  threat = 43,
  refuel_acquiring = 46,
  refuel_response = 48,
  landing_stopped = 49,
  recovery = 62,
  fill_up = 69,
  afterburner = 75,
};

class runtime {
private:
  sample_bank bank;
  sample_voice effects;
  bool enabled;

public:
  runtime(std::span<sample_definition const> definitions, resources::archive const &game, unsigned int output_rate, bool sound_enabled);
  bool sound_enabled() const;
  void enable_sound(bool enabled);
  void advance(simulation::timer_ticks elapsed);
  void sample(sample_priority priority, unsigned int id);
  void sample(sample_priority priority, sample_id id);
  void sequence(sample_priority priority, std::initializer_list<unsigned int> ids);
  void render(std::span<float> stereo) noexcept;
};

} // namespace tfx::audio
