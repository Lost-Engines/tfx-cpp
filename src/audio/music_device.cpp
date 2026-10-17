#include "music_device.h"
#include "audio/midi_stream.h"
#include "audio/osl_la_driver.h"

namespace tfx::audio {
namespace {

class la_music_device final : public music_device {
private:
  std::unique_ptr<midi_receiver> receiver;
  midi_stream stream;
  osl_la_driver callbacks;

public:
  la_music_device(std::span<uint8_t const> const launcher, std::unique_ptr<midi_receiver> receiver) :
    receiver{std::move(receiver)}, stream{*this->receiver},
    callbacks{launcher,[this](uint8_t const byte) { stream.byte(byte); }} {}
  osl_device_driver &driver() override { return callbacks; }
  void render(std::span<float> const stereo) override { receiver->render(stereo); }
};

} // namespace

std::unique_ptr<music_device> make_la_music_device(std::span<uint8_t const> const launcher,
    std::unique_ptr<midi_receiver> receiver) {
  if(!receiver) throw std::invalid_argument{"music device requires a MIDI receiver"};
  return std::make_unique<la_music_device>(launcher,std::move(receiver));
}

} // namespace tfx::audio
