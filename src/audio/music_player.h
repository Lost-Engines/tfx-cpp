#pragma once

#include <mutex>
#include <filesystem>
#include "audio/music_device.h"
#include "audio/music_catalogue.h"
#include "audio/music_clock.h"
#include "audio/osl_sequencer.h"
#include "resources/archive.h"

namespace tfx::audio {

class music_player {
private:
  resources::archive const &game;
  music_catalogue catalogue;
  std::unique_ptr<music_device> device;
  osl_sequencer sequencer;
  music_clock clock;
  mutable std::mutex mutex;
  std::optional<osl_resource_id> resource;
  std::optional<osl_playing_id> playing;
  std::optional<uint8_t> preselected;
  bool enabled;
  void stop_locked();

public:
  music_player(resources::archive const &game, std::span<uint8_t const> launcher,
    std::unique_ptr<music_device> device, unsigned int output_rate, bool enabled = true);
  music_player(resources::archive const &game, std::span<uint8_t const> launcher,
    std::filesystem::path const &rom_directory, unsigned int output_rate, bool enabled = true);
  void select(int16_t index);
  void stop();
  void enable(bool enabled);
  bool is_enabled() const;
  void render(std::span<float> stereo);
};

} // namespace tfx::audio
