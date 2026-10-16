#pragma once

#include "missions/initialisation.h"
#include "simulation/timing.h"

namespace tfx::missions {

using mission_tick = uint32_t;

class timeline {
private:
  setup const &initialisation;
  mission_tick elapsed_ticks{0};
  std::vector<uint8_t> delivered_messages;
  std::vector<uint8_t> dispatched_events;

public:
  explicit timeline(setup const &source);
  void reset(mission_tick elapsed = 0);
  std::vector<unsigned int> begin_frame();
  std::vector<unsigned int> finish_frame(simulation::timer_ticks elapsed);
  mission_tick elapsed() const;
  mission_tick time_of_day() const;
};

} // namespace tfx::missions
