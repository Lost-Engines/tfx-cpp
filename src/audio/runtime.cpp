#include "runtime.h"
#include <algorithm>
#include <utility>

namespace tfx::audio {

namespace {
std::variant<sample_voice,gus_samples> make_effects(sample_bank const &bank, unsigned int const rate,
    std::optional<gus_parameters> const &gravis) {
  if(!gravis) return std::variant<sample_voice,gus_samples>{std::in_place_type<sample_voice>,bank,rate};
  std::vector<gus_sample_data> samples;
  for(unsigned int index{0}; index != bank.entries().size(); ++index) samples.push_back({
    .pcm{bank.pcm(index)},
    .rate{bank.entries()[index].rate},
    .retrigger_delay{bank.entries()[index].retrigger_delay},
  });
  return std::variant<sample_voice,gus_samples>{std::in_place_type<gus_samples>,samples,*gravis,rate};
}
}
runtime::runtime(std::span<sample_definition const> const definitions, resources::archive const &game,
    unsigned int const output_rate, sound_device const device, std::unique_ptr<music_player> music, std::optional<gus_parameters> const &gravis) :
    bank{definitions,game}, effects{make_effects(bank,output_rate,gravis)}, available{device != sound_device::none},
    sampled{device == sound_device::sound_blaster || device == sound_device::sound_blaster16 || device == sound_device::gravis},
    enabled{available}, music{std::move(music)} {
  std::visit([&](auto &output) { output.enable(enabled && sampled); },effects);
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
void runtime::music_cue(music_cue_id const cue) { music_cue(std::to_underlying(cue)); }
void runtime::lapc_effect(lapc_effect_cue const cue) { if(music) music->effect(cue); }
bool runtime::sound_enabled() const { return enabled; }
void runtime::enable_sound(bool const value) { enabled = available && value;std::visit([&](auto &device) { device.enable(enabled && sampled); },effects); }
void runtime::advance(simulation::timer_ticks const elapsed) { std::visit([&](auto &device) { device.advance(elapsed); },effects); }
void runtime::sample(sample_priority const priority, unsigned int const id) { sequence(priority,{&id,1}); }
void runtime::sample(sample_priority const priority, sample_id const id) { sample(priority,std::to_underlying(id)); }
void runtime::sequence(sample_priority const priority, std::initializer_list<unsigned int> const ids) { sequence(priority,std::span<unsigned int const>{ids}); }
void runtime::sequence(sample_priority const priority, std::span<unsigned int const> const ids) { std::visit([&](auto &device) { device.submit(priority,ids); },effects); }
void runtime::render(std::span<float> const stereo) noexcept {
  std::ranges::fill(stereo,0);
  // Device callbacks must not propagate exceptions into the platform backend.
  try { if(music) music->render(stereo);std::visit([&](auto &device) { device.render(stereo); },effects); } catch(...) { std::ranges::fill(stereo,0); }
}

} // namespace tfx::audio
