#pragma once

#include <cfloat>
#include <cmath>
#include "math/calculation.h"

#if defined(TFX_SOFT_X87)
#include "softfloat3_ext.h"
#endif

namespace tfx::math::x87 {

#if defined(TFX_SOFT_X87)

// SoftFloat hosts keep Watcom's 53-bit arithmetic via floating_environment.
// Transcendentals use the Bochs SoftFloat extensions (full 64-bit significand),
// matching the portable path needed on Apple Silicon.
inline calculation atan2(calculation const y, calculation const x) {
  // Bochs extFloat80_atan(a, b) computes atan(b/a), matching x87 FPATAN
  // with ST(0)=a (x) and ST(1)=b (y).
  return calculation{extFloat80_atan(x.bits(), y.bits())};
}

inline calculation sin(calculation const value) {
  extFloat80_t bits{value.bits()};
  extFloat80_sin(bits);
  return calculation{bits};
}

inline calculation cos(calculation const value) {
  extFloat80_t bits{value.bits()};
  extFloat80_cos(bits);
  return calculation{bits};
}

inline calculation tan(calculation const value) {
  extFloat80_t bits{value.bits()};
  extFloat80_tan(bits);
  return calculation{bits};
}

#else

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

inline long double sin(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fsin" : "=t"(result) : "0"(value));
  return result;
#else
  return std::sin(value);
#endif
}
inline long double cos(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fcos" : "=t"(result) : "0"(value));
  return result;
#else
  return std::cos(value);
#endif
}

inline long double tan(long double const value) {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  long double result;
  __asm__("fptan; fstp %%st(0)" : "=t"(result) : "0"(value));
  return result;
#else
  return std::tan(value);
#endif
}

#endif

} // namespace tfx::math::x87
