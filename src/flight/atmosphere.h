#pragma once

#include <cstdint>
#include <optional>

namespace tfx::flight {

struct atmosphere_parameters {
  double sea_level_density{1.225};
  double temperature_lapse_per_metre{.0065};
  double temperature_lapse_limit_metres{11000};
};
struct atmosphere_sample {
  double density{0};
  double sea_level_kelvin{0};
  double local_kelvin{0};
  double sound_metres_per_second{0};
};

// Native 0x992fc. The atmosphere's retained kilometre altitude and physical
// down-coordinate are distinct inputs, as they are at the original boundary.
// An absent surface temperature selects the original disabled-realism value.
atmosphere_sample sample_atmosphere(double altitude_km, double down_metres, std::optional<int16_t> surface_celsius = {}, atmosphere_parameters const &parameters = {});

} // namespace tfx::flight
