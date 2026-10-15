#pragma once

#include <cstdint>
#include <span>
#include <vector>

namespace tfx::world {

using timer_ticks = uint16_t;
unsigned int constexpr pit_input_hz{1193182}, pit_divisor{21845};
double constexpr timer_hz{static_cast<double>(pit_input_hz) / pit_divisor};
timer_ticks constexpr animation_interval{7}, maximum_animation_backlog{100};

enum class stream_action { value_written, finished, event_requested };
struct stream_step {
  stream_action action;
  int16_t event{0};
};

class parameter_player {
private:
  std::vector<uint16_t> words;
  unsigned int cursor{0};
  bool finished{false};

public:
  parameter_player(std::span<uint16_t const> source);
  stream_step tick(uint8_t &parameter);
};

class animation_clock {
private:
  timer_ticks accumulated{0};

public:
  bool advance(timer_ticks elapsed);
  int16_t remainder() const;
};

} // namespace tfx::world
