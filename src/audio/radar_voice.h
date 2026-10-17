#pragma once

#include <cstdint>
#include <vector>

namespace tfx::audio {

// Native 0xa4e80: one urgent spoken bearing/altitude report, in sample-slot order.
std::vector<unsigned int> radar_report_voice(int16_t bearing_degrees, int16_t altitude_thousands);

} // namespace tfx::audio
