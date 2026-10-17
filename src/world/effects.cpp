#include "effects.h"
#include <bit>
#include <stdexcept>
#include <utility>

namespace tfx::world {

void effect_pool::reset() {
  next = effect_capacity - 1;
  count = 0;
}
effect_slot effect_pool::spawn(vec3<int32_t> const &position, effect_kind const kind) {
  if(std::to_underlying(kind) >= effect_kind_count) throw std::out_of_range{"unknown transient effect kind"};
  effect_slot const slot{next};
  records[slot] = {
    .position{math::signed_word(static_cast<uint16_t>(position.x)),math::signed_word(static_cast<uint16_t>(position.y)),math::signed_word(static_cast<uint16_t>(position.z))},
    .kind{kind},
  };
  next = next ? next - 1 : effect_capacity - 1;
  if(count != effect_capacity) ++count;
  return slot;
}
effect_record const &effect_pool::record(effect_slot const slot) const { return records.at(slot); }

vec3<int16_t> effect_origin(vec3<int16_t> const &local, vec3<int16_t> const &origin, math::angle const heading) {
  vec3<int32_t> rotated{local};
  switch(heading >> 14) {
  case 1: rotated = {local.z,local.y,-static_cast<int32_t>(local.x)};break;
  case 2: rotated = {-static_cast<int32_t>(local.x),local.y,-static_cast<int32_t>(local.z)};break;
  case 3: rotated = {-static_cast<int32_t>(local.z),local.y,local.x};break;
  default: break;
  }
  return {
    math::signed_word(static_cast<uint16_t>(rotated.x + origin.x)),
    math::signed_word(static_cast<uint16_t>(rotated.y + origin.y)),
    math::signed_word(static_cast<uint16_t>(rotated.z + origin.z)),
  };
}

vec3<int32_t> effect_position(vec3<int16_t> const &position, vec3<int32_t> const &reference) {
  vec3<int32_t> result;
  for(unsigned int axis{0}; axis != 3; ++axis) {
    int32_t const difference{math::signed_word(static_cast<uint16_t>(position[axis] - static_cast<int16_t>(static_cast<uint16_t>(reference[axis]))))};
    result[axis] = std::bit_cast<int32_t>(static_cast<uint32_t>(reference[axis]) + static_cast<uint32_t>(difference));
  }
  return result;
}

} // namespace tfx::world
