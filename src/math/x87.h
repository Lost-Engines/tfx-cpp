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
#endif // (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
}

inline long double sin(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fsin" : "=t"(result) : "0"(value));
  return result;
#else
  return std::sin(value);
#endif // (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
}
inline long double cos(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fcos" : "=t"(result) : "0"(value));
  return result;
#else
  return std::cos(value);
#endif // (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
}

inline long double tan(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fptan; fstp %%st(0)" : "=t"(result) : "0"(value));
  return result;
#else
  return std::tan(value);
#endif // (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
}

} // namespace tfx::math::x87
