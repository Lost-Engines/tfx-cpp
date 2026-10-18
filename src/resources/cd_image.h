#pragma once

#include <filesystem>
#include <string_view>
#include "binary.h"

namespace tfx::resources {

unsigned int constexpr cd_sector_bytes{2352};
unsigned int constexpr cd_data_bytes{2048};
unsigned int constexpr cd_sectors_per_second{75};
unsigned int constexpr cd_sample_rate{44100};
unsigned int constexpr cd_channels{2};
unsigned int constexpr cd_sample_bytes{2};

struct cd_track {
  unsigned int number;
  bool audio;
  std::filesystem::path file;
  unsigned int sector_bytes;
  uint32_t file_sector;
  uint32_t sectors;
  uint32_t disc_sector;
};

// CUE offsets remain relative to their FILE; disc positions also include
// stored pregaps and explicit PREGAP/POSTGAP directives. No image is loaded whole.
class cd_image {
private:
  std::vector<cd_track> tracks_;

public:
  explicit cd_image(std::filesystem::path const &cue);
  std::span<cd_track const> tracks() const;
  cd_track const &track(unsigned int number) const;
  bytes read_file(std::string_view name) const;
};

// Materialise only the reference runtime assets; settings and pilot saves
// already in the destination are retained. The original DOS installer is not run.
void install_reference_cd(std::filesystem::path const &cue, std::filesystem::path const &destination);

} // namespace tfx::resources
