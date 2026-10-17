#pragma once

#include <initializer_list>
#include "audio/sample_voice.h"
#include "audio/requests.h"
#include "audio/music_player.h"

namespace tfx::audio {

class runtime {
private:
  sample_bank bank;
  sample_voice effects;
  bool const available;
  bool enabled;
  std::unique_ptr<music_player> music;

public:
  runtime(std::span<sample_definition const> definitions, resources::archive const &game, unsigned int output_rate, bool sound_enabled, std::unique_ptr<music_player> music = {});
  bool sound_available() const;
  bool sound_enabled() const;
  bool music_available() const;
  bool music_enabled() const;
  void enable_music(bool enabled);
  void select_music(int16_t index);
  void stop_music();
  void begin_flight(flight_audio_state const &state);
  void end_flight();
  void update_flight(flight_audio_state const &state);
  void music_cue(uint8_t cue);
  void music_cue(music_cue_id cue);
  void enable_sound(bool enabled);
  void advance(simulation::timer_ticks elapsed);
  void sample(sample_priority priority, unsigned int id);
  void sample(sample_priority priority, sample_id id);
  void sequence(sample_priority priority, std::initializer_list<unsigned int> ids);
  void sequence(sample_priority priority, std::span<unsigned int const> ids);
  void render(std::span<float> stereo) noexcept;
};

} // namespace tfx::audio
