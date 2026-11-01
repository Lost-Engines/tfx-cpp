#pragma once

// Host arithmetic type for faithful flight intermediates.
// On x87 hosts this is long double (64-bit significand). Elsewhere — and when
// TFX_SOFT_X87 is forced for verification — it is the SoftFloat float80 wrapper.

#include <limits>
#include <numbers>

#if defined(TFX_SOFT_X87)
#include "math/float80.h"
#endif

namespace tfx::math {

#if defined(TFX_SOFT_X87)
using calculation = float80;
#else
using calculation = long double;
#endif

// Prefer calculation{1} / x over 1.0L / x. The latter divides in host long
// double before converting, which bypasses SoftFloat on non-x87 builds.

inline constexpr bool calculation_is_x87_precision =
  std::numeric_limits<calculation>::digits == 64;

// x87 FLDPI / long-double pi_v significand. On SoftFloat hosts, pi_v<long
// double> is only double-width and must not be used for extended constants.
inline calculation calculation_pi() {
#if defined(TFX_SOFT_X87)
  extFloat80_t bits{};
  bits.signExp = 0x4000;
  bits.signif = 0xc90fdaa22168c235ull;
  return calculation{bits};
#else
  return std::numbers::pi_v<long double>;
#endif
}

// Classic x87 pi/2 significand (same mantissa as FLDPI, exponent 0x3fff).
// Do not form this as calculation_pi()/2 under SoftFloat: Watcom PC=53 would
// round the quotient and change later pi/2-asin results. Hardware compilers
// typically fold std::numbers::pi_v / 2 to the full constant.
inline calculation calculation_pi2() {
#if defined(TFX_SOFT_X87)
  extFloat80_t bits{};
  bits.signExp = 0x3fff;
  bits.signif = 0xc90fdaa22168c235ull;
  return calculation{bits};
#else
  return std::numbers::pi_v<long double> / 2;
#endif
}

} // namespace tfx::math
