#pragma once

// Soft IEEE extended-precision value used when the host has no x87 long double.
// Arithmetic follows SoftFloat's extFloat80 with Watcom's 53-bit precision
// control while transcendental helpers keep full 64-bit significands.

#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <type_traits>

extern "C" {
#include "softfloat.h"
}

namespace tfx::math {

class float80 {
  extFloat80_t value{};

  static float80 from_bits(extFloat80_t const bits) {
    float80 result;
    result.value = bits;
    return result;
  }

  static float64_t f64_bits(double const number) {
    float64_t bits{};
    std::memcpy(&bits, &number, sizeof(bits));
    return bits;
  }

  static float32_t f32_bits(float const number) {
    float32_t bits{};
    std::memcpy(&bits, &number, sizeof(bits));
    return bits;
  }

public:
  float80() = default;

  float80(extFloat80_t const bits) : value{bits} {}

  template<class T, std::enable_if_t<std::is_integral_v<T>, int> = 0>
  float80(T const integer) : value{i64_to_extF80(static_cast<std::int64_t>(integer))} {}

  float80(float const number) : value{f32_to_extF80(f32_bits(number))} {}

  float80(double const number) : value{f64_to_extF80(f64_bits(number))} {}

  float80(long double const number) {
#if (defined(__i386__) || defined(__x86_64__)) && (LDBL_MANT_DIG == 64)
    std::memcpy(&value, &number, 10);
#else
    value = f64_to_extF80(f64_bits(static_cast<double>(number)));
#endif
  }

  explicit operator float() const {
    auto const bits{extF80_to_f32(value)};
    float result{};
    std::memcpy(&result, &bits, sizeof(result));
    return result;
  }

  explicit operator double() const {
    auto const bits{extF80_to_f64(value)};
    double result{};
    std::memcpy(&result, &bits, sizeof(result));
    return result;
  }

  explicit operator long double() const {
#if (defined(__i386__) || defined(__x86_64__)) && (LDBL_MANT_DIG == 64)
    long double result{};
    std::memcpy(&result, &value, 10);
    return result;
#else
    return static_cast<long double>(static_cast<double>(*this));
#endif
  }

  // Match common x87 FISTP truncation toward zero used around flight code.
  explicit operator std::int64_t() const {
    return extF80_to_i64(value, softfloat_round_minMag, false);
  }
  explicit operator std::uint64_t() const {
    return extF80_to_ui64(value, softfloat_round_minMag, false);
  }
  explicit operator std::int32_t() const {
    return static_cast<std::int32_t>(static_cast<std::int64_t>(*this));
  }
  explicit operator std::uint32_t() const {
    return static_cast<std::uint32_t>(static_cast<std::uint64_t>(*this));
  }
  explicit operator std::int16_t() const {
    return static_cast<std::int16_t>(static_cast<std::int64_t>(*this));
  }
  explicit operator std::uint16_t() const {
    return static_cast<std::uint16_t>(static_cast<std::uint64_t>(*this));
  }

  extFloat80_t const &bits() const { return value; }
  extFloat80_t &bits() { return value; }

  friend float80 operator+(float80 const left, float80 const right) {
    return from_bits(extF80_add(left.value, right.value));
  }
  friend float80 operator-(float80 const left, float80 const right) {
    return from_bits(extF80_sub(left.value, right.value));
  }
  friend float80 operator*(float80 const left, float80 const right) {
    return from_bits(extF80_mul(left.value, right.value));
  }
  friend float80 operator/(float80 const left, float80 const right) {
    return from_bits(extF80_div(left.value, right.value));
  }
  friend float80 operator+(float80 const value) { return value; }
  friend float80 operator-(float80 const value) {
    extFloat80_t bits{value.value};
    bits.signExp ^= 0x8000;
    return from_bits(bits);
  }

  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator+(float80 const left, T const right) { return left + float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator+(T const left, float80 const right) { return float80{left} + right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator-(float80 const left, T const right) { return left - float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator-(T const left, float80 const right) { return float80{left} - right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator*(float80 const left, T const right) { return left * float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator*(T const left, float80 const right) { return float80{left} * right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator/(float80 const left, T const right) { return left / float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend float80 operator/(T const left, float80 const right) { return float80{left} / right; }

  float80 &operator+=(float80 const right) { return *this = *this + right; }
  float80 &operator-=(float80 const right) { return *this = *this - right; }
  float80 &operator*=(float80 const right) { return *this = *this * right; }
  float80 &operator/=(float80 const right) { return *this = *this / right; }

  friend bool operator==(float80 const left, float80 const right) {
    return extF80_eq(left.value, right.value);
  }
  friend bool operator!=(float80 const left, float80 const right) { return !(left == right); }
  friend bool operator<(float80 const left, float80 const right) {
    return extF80_lt(left.value, right.value);
  }
  friend bool operator>(float80 const left, float80 const right) { return right < left; }
  friend bool operator<=(float80 const left, float80 const right) {
    return extF80_le(left.value, right.value);
  }
  friend bool operator>=(float80 const left, float80 const right) { return right <= left; }

  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator==(float80 const left, T const right) { return left == float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator==(T const left, float80 const right) { return float80{left} == right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator!=(float80 const left, T const right) { return !(left == right); }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator!=(T const left, float80 const right) { return !(left == right); }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator<(float80 const left, T const right) { return left < float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator<(T const left, float80 const right) { return float80{left} < right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator>(float80 const left, T const right) { return left > float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator>(T const left, float80 const right) { return float80{left} > right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator<=(float80 const left, T const right) { return left <= float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator<=(T const left, float80 const right) { return float80{left} <= right; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator>=(float80 const left, T const right) { return left >= float80{right}; }
  template<class T, std::enable_if_t<std::is_arithmetic_v<T>, int> = 0>
  friend bool operator>=(T const left, float80 const right) { return float80{left} >= right; }
};

inline float80 sqrt(float80 const value) {
  return float80{extF80_sqrt(value.bits())};
}

inline float80 abs(float80 const value) {
  extFloat80_t bits{value.bits()};
  bits.signExp &= 0x7fff;
  return float80{bits};
}

inline float80 trunc(float80 const value) {
  return float80{extF80_roundToInt(value.bits(), softfloat_round_minMag, false)};
}

// Soft FSIN/FCOS/FPTAN/FPATAN live in math/x87.h via Bochs SoftFloat extensions.
// pow has no x87 counterpart in the flight path; keep a double stand-in.
inline float80 pow(float80 const base, float80 const exponent) {
  return float80{std::pow(static_cast<double>(base), static_cast<double>(exponent))};
}

inline bool isfinite(float80 const value) {
  auto const exponent{static_cast<std::uint16_t>(value.bits().signExp & 0x7fffu)};
  return exponent != 0x7fffu;
}

inline bool isnan(float80 const value) {
  auto const bits{value.bits()};
  return (bits.signExp & 0x7fffu) == 0x7fffu && (bits.signif & 0x7fffffffffffffffull) != 0;
}

inline bool isinf(float80 const value) {
  auto const bits{value.bits()};
  return (bits.signExp & 0x7fffu) == 0x7fffu && (bits.signif & 0x7fffffffffffffffull) == 0;
}

} // namespace tfx::math

template<>
class std::numeric_limits<tfx::math::float80> {
public:
  static constexpr bool is_specialized{true};
  static constexpr bool is_signed{true};
  static constexpr bool is_integer{false};
  static constexpr bool is_exact{false};
  static constexpr bool has_infinity{true};
  static constexpr bool has_quiet_NaN{true};
  static constexpr bool has_signaling_NaN{true};
  static constexpr bool has_denorm{true};
  static constexpr bool has_denorm_loss{false};
  static constexpr std::float_round_style round_style{std::round_to_nearest};
  static constexpr bool is_iec559{false};
  static constexpr bool is_bounded{true};
  static constexpr bool is_modulo{false};
  static constexpr int digits{64};
  static constexpr int digits10{18};
  static constexpr int max_digits10{21};
  static constexpr int radix{2};
  static constexpr int min_exponent{-16381};
  static constexpr int min_exponent10{-4931};
  static constexpr int max_exponent{16384};
  static constexpr int max_exponent10{4932};
  static constexpr bool traps{false};
  static constexpr bool tinyness_before{false};

  static tfx::math::float80 from_parts(std::uint64_t const signif, std::uint16_t const sign_exp) noexcept {
    extFloat80_t bits{};
    bits.signif = signif;
    bits.signExp = sign_exp;
    return tfx::math::float80{bits};
  }
  static tfx::math::float80 min() noexcept {
    return from_parts(0x8000000000000000ull, 1);
  }
  static tfx::math::float80 lowest() noexcept { return -max(); }
  static tfx::math::float80 max() noexcept {
    return from_parts(0xffffffffffffffffull, 0x7ffe);
  }
  static tfx::math::float80 epsilon() noexcept {
    return from_parts(0x8000000000000000ull, 0x3fbf);
  }
  static tfx::math::float80 round_error() noexcept { return tfx::math::float80{0.5}; }
  static tfx::math::float80 infinity() noexcept {
    return from_parts(0x8000000000000000ull, 0x7fff);
  }
  static tfx::math::float80 quiet_NaN() noexcept {
    return from_parts(0xc000000000000000ull, 0x7fff);
  }
  static tfx::math::float80 signaling_NaN() noexcept {
    return from_parts(0xa000000000000000ull, 0x7fff);
  }
  static tfx::math::float80 denorm_min() noexcept {
    return from_parts(1ull, 0);
  }
};
