#pragma once

#include <initializer_list>
#include <variant>
#include "audio/gus_samples.h"
#include "audio/sample_voice.h"
#include "audio/requests.h"
#include "audio/music_player.h"

namespace tfx::audio {

class runtime {
private:
  sample_bank bank;
  std::variant<sample_voice,gus_samples> effects;
  bool const available;
  bool const sampled;
  bool enabled;
  std::unique_ptr<music_player> music;

public:
  runtime(std::span<sample_definition const> definitions, resources::archive const &game, unsigned int output_rate,
    sound_device device, std::unique_ptr<music_player> music = {}, std::optional<gus_parameters> const &gravis = {});
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
  void lapc_effect(lapc_effect_cue cue);
  void enable_sound(bool enabled);
  void advance(simulation::timer_ticks elapsed);
  void sample(sample_priority priority, unsigned int id);
  void sample(sample_priority priority, sample_id id);
  void sequence(sample_priority priority, std::initializer_list<unsigned int> ids);
  void sequence(sample_priority priority, std::span<unsigned int const> ids);
  void render(std::span<float> stereo) noexcept;
};

} // namespace tfx::audio
