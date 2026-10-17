#include "runtime.h"
#include <algorithm>
#include <utility>

namespace tfx::audio {

runtime::runtime(std::span<sample_definition const> const definitions, resources::archive const &game,
    unsigned int const output_rate, bool const sound_enabled, std::unique_ptr<music_player> music) :
    bank{definitions,game}, effects{bank,output_rate}, available{sound_enabled}, enabled{sound_enabled}, music{std::move(music)} {
  effects.enable(enabled);
}
bool runtime::sound_available() const { return available; }
bool runtime::music_available() const { return music != nullptr; }
bool runtime::music_enabled() const { return music && music->is_enabled(); }
void runtime::enable_music(bool const value) { if(music) music->enable(value); }
void runtime::select_music(int16_t const index) { if(music) music->select(index); }
void runtime::stop_music() { if(music) music->stop(); }
void runtime::begin_flight(flight_audio_state const &state) { if(music) music->begin_flight(state); }
void runtime::end_flight() { if(music) music->end_flight(); }
void runtime::update_flight(flight_audio_state const &state) { if(music) music->update_flight(state); }
void runtime::music_cue(uint8_t const cue) { if(music) music->cue(cue); }
bool runtime::sound_enabled() const { return enabled; }
void runtime::enable_sound(bool const value) { enabled = available && value;effects.enable(enabled); }
void runtime::advance(simulation::timer_ticks const elapsed) { effects.advance(elapsed); }
void runtime::sample(sample_priority const priority, unsigned int const id) { effects.submit(priority,{&id,1}); }
void runtime::sample(sample_priority const priority, sample_id const id) { sample(priority,std::to_underlying(id)); }
void runtime::sequence(sample_priority const priority, std::initializer_list<unsigned int> const ids) { effects.submit(priority,ids); }
void runtime::render(std::span<float> const stereo) noexcept {
  std::ranges::fill(stereo,0);
  // Device callbacks must not propagate exceptions into the platform backend.
  try { if(music) music->render(stereo);effects.render(stereo); } catch(...) { std::ranges::fill(stereo,0); }
}

} // namespace tfx::audio
