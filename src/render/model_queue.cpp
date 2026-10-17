#include "model_queue.h"
#include <utility>

namespace tfx::render {

void model_queue::clear() { count = 0;current = 0;sorted = false; }
unsigned int model_queue::size() const { return count; }

void model_queue::insertion_sort() {
  for(unsigned int i{1}; i < count; ++i) {
    entry const value{entries[i]};unsigned int at{i};
    // Native C4824 moves equal priorities too. Reverse traversal consequently
    // retains its insertion/tie behaviour, including repeated full-queue sorts.
    // The explicit bound also safely handles the original sentinel value.
    while(at && value.priority <= entries[at - 1].priority) {
      entries[at] = entries[at - 1];--at;
    }
    entries[at] = value;
  }
}
void model_queue::quick_sort(int const first, int const last) {
  // Original one-based partition bounds and last-element pivot. Small runs
  // remain for the final insertion pass; changing that changes equal keys.
  int constexpr insertion_run{4};
  if(last - first <= insertion_run) return;
  auto const pivot{entries[static_cast<unsigned int>(last - 1)].priority};
  int left{first - 2},right{last - 1};
  for(;;) {
    do { ++left; } while(pivot > entries[static_cast<unsigned int>(left)].priority);
    do { --right; } while(right >= 0 && pivot < entries[static_cast<unsigned int>(right)].priority);
    if(left >= right) break;
    std::swap(entries[static_cast<unsigned int>(left)],entries[static_cast<unsigned int>(right)]);
  }
  std::swap(entries[static_cast<unsigned int>(left)],entries[static_cast<unsigned int>(last - 1)]);
  quick_sort(first,left);
  quick_sort(left + 2,last);
}
model_slot model_queue::insert(int16_t const priority) {
  model_slot const slot{current};
  if(++count < model_queue_capacity) {
    entries[current] = {
      .priority{priority},
      .slot{current},
    };
    current = static_cast<model_slot>(count);
    return slot;
  }
  if(sorted) entries.back().priority = priority;
  else entries[current] = {
    .priority{priority},
    .slot{static_cast<model_slot>(model_queue_capacity - 1)},
  };
  count = model_queue_capacity;
  // C4930 switches its own branch after the first fill. Later insertions
  // replace the previous last entry and reuse that entry's payload slot.
  insertion_sort();current = entries.back().slot;sorted = true;
  return slot;
}
std::vector<model_slot> model_queue::draw_order() {
  if(!sorted) {
    unsigned int constexpr quick_sort_threshold{15};
    if(count >= quick_sort_threshold) quick_sort(1,static_cast<int>(count));
    if(count >= 2) { insertion_sort();sorted = true; }
  }
  std::vector<model_slot> result;result.reserve(count);
  for(unsigned int index{count}; index; --index) result.push_back(entries[index - 1].slot);
  return result;
}

} // namespace tfx::render
