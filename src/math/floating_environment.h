#pragma once

#include <cstdint>
#include <limits>
#include <stdexcept>

#if defined(TFX_SOFT_X87)
#include "math/float80.h"
#endif

namespace tfx::math {

// Watcom's original FPU detection/reset (0xde851 -> 0xea0fc) loads 0x127f:
// masked exceptions, nearest rounding and a 53-bit arithmetic significand.
// x87 transcendental results still retain their instruction's extended format.
class floating_environment {
private:
#if defined(TFX_SOFT_X87)
  std::uint_fast8_t previous_rounding{};
  std::uint_fast8_t previous_precision{};
  bool changed{false};
#elif (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  unsigned short previous{0};
  bool changed{false};
#endif

public:
  floating_environment() {
#if defined(TFX_SOFT_X87)
    previous_rounding = softfloat_roundingMode;
    previous_precision = extF80_roundingPrecision;
    // softfloat_round_near_even and precision 64 match control word 0x127f.
    changed = previous_rounding != softfloat_round_near_even || previous_precision != 64;
    softfloat_roundingMode = softfloat_round_near_even;
    extF80_roundingPrecision = 64;
    softfloat_exceptionFlags = 0;
#elif (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
    unsigned short constexpr native_control{0x127f};
    __asm__ volatile("fnstcw %0" : "=m"(previous));
    changed = previous != native_control;
    if(changed) __asm__ volatile("fldcw %0" : : "m"(native_control) : "memory");
#else
    throw std::runtime_error{"native numerical flight currently requires an x87 arithmetic backend"};
#endif
  }
  ~floating_environment() {
#if defined(TFX_SOFT_X87)
    if(changed) {
      softfloat_roundingMode = previous_rounding;
      extF80_roundingPrecision = previous_precision;
    }
#elif (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
    if(changed) __asm__ volatile("fldcw %0" : : "m"(previous) : "memory");
#endif
  }
  floating_environment(floating_environment const &) = delete;
  floating_environment &operator=(floating_environment const &) = delete;
};

} // namespace tfx::math
