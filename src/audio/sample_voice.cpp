#include "sample_voice.h"

namespace tfx::audio {

sample_voice::sample_voice(sample_bank const &bank, uint32_t const output_rate) : bank{bank}, scheduler{bank.scheduling()}, output_rate{output_rate} {
  if(!output_rate) throw std::invalid_argument{"PCM output rate must not be zero"};
}
void sample_voice::enable(bool const enabled) { std::lock_guard lock{mutex};scheduler.enable(enabled); }
void sample_voice::advance(simulation::timer_ticks const elapsed) { std::lock_guard lock{mutex};scheduler.advance(elapsed); }
void sample_voice::submit(sample_priority const priority, std::span<unsigned int const> const sequence) {
  std::lock_guard lock{mutex};
  auto request{scheduler.submit(priority,sequence)};
  if(request.interrupted || request.started) {
    queue = std::move(request.sequence);
    item = offset = 0;
    phase = 0;
  }
}
void sample_voice::render(std::span<float> const stereo) {
  if(stereo.size() % 2) throw std::invalid_argument{"PCM output needs complete stereo frames"};
  std::lock_guard lock{mutex};
  for(unsigned int frame{0}; frame != stereo.size() / 2; ++frame) {
    if(item == queue.size()) break;
    auto const sample{bank.pcm(queue[item])[offset]};
    float const amplitude{(static_cast<int>(sample) - 128) / 128.0f};
    stereo[frame * 2] += amplitude;
    stereo[frame * 2 + 1] += amplitude;
    phase += 1'000'000;
    while(item != queue.size()) {
      auto const duration{static_cast<uint64_t>(sound_blaster_period(bank.entries()[queue[item]].rate)) * output_rate};
      if(phase < duration) break;
      phase -= duration;
      if(++offset == bank.pcm(queue[item]).size()) { offset = 0;++item; }
    }
    if(item == queue.size()) scheduler.complete();
  }
}
sample_scheduler_state sample_voice::state() { std::lock_guard lock{mutex};return scheduler.value(); }

} // namespace tfx::audio
