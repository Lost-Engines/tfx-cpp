#include "runtime.h"
#include <algorithm>
#include <utility>

namespace tfx::audio {

runtime::runtime(std::span<sample_definition const> const definitions, resources::archive const &game,
    unsigned int const output_rate, bool const sound_enabled) : bank{definitions,game}, effects{bank,output_rate}, enabled{sound_enabled} {
  effects.enable(enabled);
}
bool runtime::sound_enabled() const { return enabled; }
void runtime::enable_sound(bool const value) { enabled = value;effects.enable(value); }
void runtime::advance(simulation::timer_ticks const elapsed) { effects.advance(elapsed); }
void runtime::sample(sample_priority const priority, unsigned int const id) { effects.submit(priority,{&id,1}); }
void runtime::sample(sample_priority const priority, sample_id const id) { sample(priority,std::to_underlying(id)); }
void runtime::sequence(sample_priority const priority, std::initializer_list<unsigned int> const ids) { effects.submit(priority,ids); }
void runtime::render(std::span<float> const stereo) noexcept {
  std::ranges::fill(stereo,0);
  // Device callbacks must not propagate exceptions into the platform backend.
  try { effects.render(stereo); } catch(...) { std::ranges::fill(stereo,0); }
}

} // namespace tfx::audio
