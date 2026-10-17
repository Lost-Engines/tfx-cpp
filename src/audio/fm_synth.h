#pragma once

#include <memory>
#include "audio/osl_fm_driver.h"

namespace tfx::audio {

class fm_synth {
private:
  struct implementation;
  std::unique_ptr<implementation> state;

public:
  explicit fm_synth(unsigned int sample_rate);
  ~fm_synth();
  void write(opl_write command);
  void render(std::span<float> stereo);
};

} // namespace tfx::audio
