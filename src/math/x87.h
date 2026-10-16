#pragma once

#include <cmath>

namespace tfx::math::x87 {

// The current native numerical backend already requires a 64-bit-significand
// long double. Keep the actual x87 transcendental rounding on x86 hosts.
inline long double atan2(long double const y, long double const x) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fpatan" : "=t"(result) : "0"(x), "u"(y) : "st(1)");
  return result;
#else
  return std::atan2(y,x);
#endif
}

} // namespace tfx::math::x87
