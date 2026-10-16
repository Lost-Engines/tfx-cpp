#include "attitude.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace tfx::math {
namespace {

int32_t wrap(int64_t const value) {
  return std::bit_cast<int32_t>(static_cast<uint32_t>(value));
}
int32_t component(int64_t const value) {
  return signed_word(static_cast<uint16_t>(wrap(value) >> matrix_fraction_bits));
}
vec3<int32_t> quantise(vec3<int64_t> const &value) {
  return {component(value.x),component(value.y),component(value.z)};
}
vec3<int32_t> unit_cross(vec3<int32_t> const &first, vec3<int32_t> const &second) {
  auto const crossed{quantise(vec3<int64_t>{first}.cross(vec3<int64_t>{second}))};
  auto const squared{vec3<int64_t>{crossed}.length_sq()};
  auto const length{integer_sqrt(static_cast<uint32_t>(wrap(squared) >> 2)) + 1};
  int32_t const divisor{signed_word(static_cast<uint16_t>(length))};
  if(!divisor) throw std::runtime_error{"degenerate native attitude normalisation"};
  return {(crossed.x * (1 << 14)) / divisor,(crossed.y * (1 << 14)) / divisor,(crossed.z * (1 << 14)) / divisor};
}

} // anonymous namespace

uint32_t integer_sqrt(uint32_t const value) {
  /// Return the native integer square-root result without relying on libm rounding at square boundaries
  auto root{static_cast<uint32_t>(std::sqrt(static_cast<double>(value)))};
  while(static_cast<uint64_t>(root) * root > value) --root;
  while(static_cast<uint64_t>(root + 1) * (root + 1) <= value) ++root;
  return root;
}

angle direction_angle(int16_t const vertical, int16_t const horizontal) {
  /// Native 0xcdc2d quantises atan2 to 1,024 phases using truncated tangent thresholds
  if(!vertical) return horizontal < 0 ? 32768 : 0;
  // native thresholds are slightly irregular; regenerating a true tangent table changes returned phases
  static std::array<uint16_t,128> constexpr thresholds{
    201,603,1005,1407,1810,2212,2613,3017,
    3420,3824,4227,4632,5035,5442,5846,6252,
    6658,7065,7473,7882,8289,8698,9107,9518,
    9930,10343,10755,11168,11583,11999,12416,12834,
    13252,13672,14091,14515,14938,15362,15787,16213,
    16641,17072,17502,17934,18367,18803,19240,19677,
    20117,20559,21003,21448,21896,22344,22795,23246,
    23700,24158,24616,25077,25542,26005,26474,26944,
    27415,27890,28368,28848,29332,29817,30303,30793,
    31288,31785,32283,32786,33291,33800,34312,34829,
    35347,35868,36394,36923,37457,37994,38533,39078,
    39627,40181,40738,41299,41863,42433,43008,43589,
    44173,44761,45353,45954,46558,47166,47784,48404,
    49029,49660,50300,50944,51594,52249,52913,53583,
    54259,54942,55631,56330,57036,57749,58468,59196,
    59933,60680,61433,62195,62965,63744,64536,65335,
  };
  uint32_t const y{static_cast<uint32_t>(vertical < 0 ? -static_cast<int32_t>(vertical) : vertical)};
  uint32_t const x{static_cast<uint32_t>(horizontal < 0 ? -static_cast<int32_t>(horizontal) : horizontal)};
  auto const octant{[](uint32_t const small, uint32_t const large){
    auto const ratio{static_cast<uint16_t>((small << 16) / large)};
    return static_cast<unsigned int>(std::upper_bound(thresholds.begin(),thresholds.end(),ratio) - thresholds.begin()) * 64;
  }};
  unsigned int result{y == x ? 8192 : y > x ? 16384 - octant(x,y) : octant(y,x)};
  if(horizontal < 0) result = 32768 - result;
  if(vertical < 0) result = 0u - result;
  return static_cast<angle>(result);
}

void attitude::rotate(rotation_axis const axis, angle const amount) {
  /// Native local rotations 0xccf4c/0xcd058/0xcd15c retain 32-bit products and signed-word stores
  auto const &sines{sine_table()};
  unsigned int const phase{static_cast<unsigned int>(amount) >> 6};
  int64_t const sine{sines[phase]}, cosine{sines[(phase + angle_steps / 4) % angle_steps]};
  auto *first{axis == rotation_axis::pitch ? &down : &right};
  auto *second{axis == rotation_axis::roll ? &down : &forward};
  auto rotated_first{quantise(vec3<int64_t>{*first} * cosine - vec3<int64_t>{*second} * sine)};
  auto rotated_second{quantise(vec3<int64_t>{*second} * cosine + vec3<int64_t>{*first} * sine)};
  *first = std::move(rotated_first);
  *second = std::move(rotated_second);
}
void attitude::normalise() {
  /// Native 0xccd3c rebuilds and normalises successive columns using cross products and integer division
  right = unit_cross(down,forward);
  down = unit_cross(forward,right);
  forward = unit_cross(right,down);
}
bool attitude::align_down(vec3f const &direction) {
  // Native 0x8e86c and 0x91c48 build a down axis, then right/down cross
  // products. Their float stores differ from the integer normalise() path.
  using calculation = long double;
  float constexpr normalised_word{3.0518509447574615e-05f}, word_scale{32767};
  double constexpr minimum_length{.001};
  auto const length{[](vec3f const &vector) {
    calculation const x{vector.x}, y{vector.y}, z{vector.z};
    return std::sqrt(x * x + y * y + z * z);
  }};
  auto const normalised{[](int32_t const value) { return static_cast<calculation>(signed_word(static_cast<uint16_t>(value))) * normalised_word; }};
  auto const words{[&](vec3f const &vector, float const magnitude) {
    calculation const inverse{1.0L / magnitude};
    auto const component{[&](float const value) { return static_cast<int32_t>(signed_word(static_cast<uint16_t>(static_cast<int32_t>(static_cast<calculation>(value) * inverse * word_scale)))); }};
    return vec3<int32_t>{component(vector.x),component(vector.y),component(vector.z)};
  }};
  auto const crossed{[&](vec3<int32_t> const &a, vec3<int32_t> const &b) {
    vec3f result;
    for(unsigned int axis{0}; axis != 3; ++axis) {
      unsigned int const next{(axis + 1) % 3}, last{(axis + 2) % 3};
      float const first{static_cast<float>(normalised(a[next]))};
      float const product{static_cast<float>(normalised(b[last]) * first)};
      float const second{static_cast<float>(normalised(a[last]))};
      result[axis] = static_cast<float>(product - normalised(b[next]) * second);
    }
    return result;
  }};
  calculation const down_length{length(direction)};
  if(down_length < minimum_length) return false;
  auto const new_down{words(direction,static_cast<float>(down_length))};
  auto const right_direction{crossed(new_down,forward)};
  calculation const right_length{length(right_direction)};
  if(right_length < minimum_length) return false;
  auto const new_right{words(right_direction,static_cast<float>(right_length))};
  auto const forward_direction{crossed(new_right,new_down)};
  vec3<int32_t> new_forward;
  for(unsigned int axis{0}; axis != 3; ++axis) new_forward[axis] = signed_word(static_cast<uint16_t>(static_cast<int32_t>(static_cast<calculation>(forward_direction[axis]) * word_scale)));
  right = new_right;
  down = new_down;
  forward = new_forward;
  return true;
}
attitude attitude::transposed() const {
  return {
    .right{right.x,down.x,forward.x},
    .down{right.y,down.y,forward.y},
    .forward{right.z,down.z,forward.z},
  };
}
vec3<angle> attitude::angles() const {
  /// Native 0xcd574/0xcd5a8/0xcd5c4 recover quantised pitch, heading and roll from the stored basis
  auto const horizontal_length{integer_sqrt(static_cast<uint32_t>(static_cast<int64_t>(forward.x) * forward.x + static_cast<int64_t>(forward.z) * forward.z))};
  auto const pitch{static_cast<angle>(-direction_angle(static_cast<int16_t>(-forward.y),static_cast<int16_t>(horizontal_length)))};
  auto const heading{direction_angle(static_cast<int16_t>(forward.x),static_cast<int16_t>(forward.z))};
  int32_t const roll_horizontal{wrap(static_cast<int64_t>(right.x) * forward.z - static_cast<int64_t>(right.z) * forward.x) >> 15};
  return {pitch,heading,static_cast<angle>(-direction_angle(static_cast<int16_t>(right.y),static_cast<int16_t>(roll_horizontal)))};
}

} // namespace tfx::math
