#pragma once

#include <array>
#include <cstdint>
#include <vector>

namespace tfx::render {

unsigned int constexpr model_queue_capacity{348};
using model_slot = uint16_t;

// Native C488D/C4930/C48E1: payloads belong to the caller; this owner retains
// the original slot reuse, signed priorities, tie ordering and queue bound.
class model_queue {
private:
  struct entry {
    int16_t priority;
    model_slot slot;
  };
  std::array<entry,model_queue_capacity> entries{};
  unsigned int count{0};
  model_slot current{0};
  bool sorted{false};
  void quick_sort(int first, int last);
  void insertion_sort();

public:
  void clear();
  model_slot insert(int16_t priority);
  std::vector<model_slot> draw_order();
  unsigned int size() const;
};

} // namespace tfx::render
