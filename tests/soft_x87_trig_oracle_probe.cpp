#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include "math/calculation.h"
#include "math/floating_environment.h"
#include "math/x87.h"

namespace {

using calculation = tfx::math::calculation;

#if defined(TFX_SOFT_X87)
std::string dump80(calculation const value) {
  auto const bits{value.bits()};
  std::ostringstream out;
  out << std::hex << std::setfill('0') << std::setw(4) << bits.signExp << ':'
      << std::setw(16) << bits.signif;
  return out.str();
}
#else
std::string dump80(calculation const value) {
#if !((defined(__i386__) || defined(__x86_64__)) && (LDBL_MANT_DIG == 64))
  (void)value;
  throw std::runtime_error{"trig oracle needs hardware x87 or SoftFloat"};
#else
  unsigned char raw[10]{};
  long double const stored{value};
  std::memcpy(raw, &stored, 10);
  std::uint64_t signif{};
  std::uint16_t sign_exp{};
  std::memcpy(&signif, raw, 8);
  std::memcpy(&sign_exp, raw + 8, 2);
  std::ostringstream out;
  out << std::hex << std::setfill('0') << std::setw(4) << sign_exp << ':'
      << std::setw(16) << signif;
  return out.str();
#endif
}
#endif

std::string dump64(double const value) {
  auto const bits{std::bit_cast<std::uint64_t>(value)};
  std::ostringstream out;
  out << std::hex << std::setfill('0') << std::setw(16) << bits;
  return out.str();
}

void emit_trig(char const *const label, double const arg_host) {
  calculation const arg{arg_host};
  calculation const sin_v{tfx::math::x87::sin(arg)};
  calculation const cos_v{tfx::math::x87::cos(arg)};
  calculation const tan_v{tfx::math::x87::tan(arg)};
  std::cout << label
            << " arg=" << dump80(arg)
            << " sin=" << dump80(sin_v)
            << " cos=" << dump80(cos_v)
            << " tan=" << dump80(tan_v)
            << " sin_dbl=" << dump64(static_cast<double>(sin_v))
            << " cos_dbl=" << dump64(static_cast<double>(cos_v))
            << " tan_dbl=" << dump64(static_cast<double>(tan_v))
            << '\n';
}

void emit_atan2(char const *const label, double const y_host, double const x_host) {
  calculation const y{y_host};
  calculation const x{x_host};
  calculation const atan_v{tfx::math::x87::atan2(y, x)};
  std::cout << label
            << " y=" << dump80(y)
            << " x=" << dump80(x)
            << " atan2=" << dump80(atan_v)
            << " atan2_dbl=" << dump64(static_cast<double>(atan_v))
            << '\n';
}

} // namespace

int main() try {
#if !defined(TFX_SOFT_X87) && !((defined(__i386__) || defined(__x86_64__)) && (LDBL_MANT_DIG == 64))
  std::cout << "SKIP: trig oracle needs hardware x87 or SoftFloat\n";
  return 77;
#else
  tfx::math::floating_environment const environment;

  // Dense angle grid matching soft_x87_transcendental_test coverage scale.
  for(int i{-200}; i <= 200; ++i) {
    double const arg{i * 0.05}; // [-10, 10]
    char label[32];
    std::snprintf(label, sizeof label, "trig_%+04d", i);
    emit_trig(label, arg);
  }

  for(int yi{-20}; yi <= 20; ++yi) {
    for(int xi{-20}; xi <= 20; ++xi) {
      if(yi == 0 && xi == 0) continue;
      char label[32];
      std::snprintf(label, sizeof label, "atan2_%+03d_%+03d", yi, xi);
      emit_atan2(label, yi * 0.25, xi * 0.25);
    }
  }

  return 0;
#endif
} catch(std::exception const &error) {
  std::cerr << error.what() << '\n';
  return 1;
}
