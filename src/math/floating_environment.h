#pragma once

#include <limits>
#include <stdexcept>

namespace tfx::math {

// Watcom's original FPU detection/reset (0xde851 -> 0xea0fc) loads 0x127f:
// masked exceptions, nearest rounding and a 53-bit arithmetic significand.
// x87 transcendental results still retain their instruction's extended format.
class floating_environment {
private:
  unsigned short previous{0};
  bool changed{false};

public:
  floating_environment() {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
    unsigned short constexpr native_control{0x127f};
    __asm__ volatile("fnstcw %0" : "=m"(previous));
    changed = previous != native_control;
    if(changed) __asm__ volatile("fldcw %0" : : "m"(native_control) : "memory");
#else
    throw std::runtime_error{"native numerical flight currently requires an x87 arithmetic backend"};
#endif
  }
  ~floating_environment() {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
    if(changed) __asm__ volatile("fldcw %0" : : "m"(previous) : "memory");
#endif
  }
  floating_environment(floating_environment const &) = delete;
  floating_environment &operator=(floating_environment const &) = delete;
};

} // namespace tfx::math
