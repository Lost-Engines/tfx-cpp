#include "music_player.h"
#include <algorithm>
#include "audio/la_synth.h"

namespace tfx::audio {

music_player::music_player(resources::archive const &game, std::span<uint8_t const> const launcher,
    std::filesystem::path const &directory, unsigned int const output_rate, bool const enabled) :
    music_player{game,launcher,make_la_music_device(launcher,std::make_unique<la_synth>(directory,output_rate)),output_rate,enabled} {}
music_player::music_player(resources::archive const &game, std::span<uint8_t const> const launcher,
    std::unique_ptr<music_device> device, unsigned int const output_rate, bool const enabled) :
    game{game}, catalogue{launcher}, device{std::move(device)}, clock{output_rate}, enabled{enabled} {
  if(!this->device) throw std::invalid_argument{"music player requires a device"};
  sequencer.register_device(this->device->driver());
  this->device->driver().initialise();
  // Let the reset settle before the first musical timeline. Uploading patches
  // later does not reset the chip, its reverb or the persistent UART stream.
  std::vector<float> settling(output_rate / 10u * 2u);
  this->device->render(settling);
}
void music_player::stop_locked() {
  if(playing) { sequencer.stop(*playing);playing.reset(); }
  if(resource) { sequencer.release(*resource);resource.reset(); }
}
void music_player::select(int16_t const requested) {
  std::lock_guard lock{mutex};
  uint8_t index{static_cast<uint8_t>(requested)};
  if(!preselected && index >= 10) { preselected = index;return; }
  if(preselected) { index = *preselected;preselected.reset(); }
  stop_locked();
  auto const files{catalogue.files(device->driver().device_type())};
  if(index >= files.size()) throw std::runtime_error{"native music index exceeds its filename list"};
  // The original loader returns an unavailable resource when a named file is
  // absent (including the retail FM antiarm entry); gameplay continues.
  if(!game.contains(files[index])) return;
  resource = sequencer.load(game.read(files[index]));
  if(enabled) playing = sequencer.play(*resource);
}
void music_player::stop() { std::lock_guard lock{mutex};stop_locked(); }
void music_player::enable(bool const value) {
  std::lock_guard lock{mutex};
  if(enabled == value) return;
  enabled = value;
  if(playing) sequencer.volume(*playing,enabled ? 75 : 0);
}
bool music_player::is_enabled() const { std::lock_guard lock{mutex};return enabled; }
void music_player::render(std::span<float> const stereo) {
  if(stereo.size() % 2) throw std::invalid_argument{"music output requires complete stereo frames"};
  std::lock_guard lock{mutex};
  unsigned int frames{0};
  while(frames != stereo.size() / 2) {
    while(clock.due()) { clock.consume();if(enabled) sequencer.tick(); }
    auto const count{static_cast<unsigned int>(std::min<size_t>(clock.until_tick(),stereo.size() / 2 - frames))};
    device->render(stereo.subspan(frames * 2,count * 2));
    clock.advance(count);
    frames += count;
  }
}

} // namespace tfx::audio
