#include <bit>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "math/calculation.h"
#include "math/floating_environment.h"
#include "math/x87.h"

namespace {

using calculation = tfx::math::calculation;
using std::sqrt;

// Match aerodynamic_guidance bank_margin.
double constexpr bank_margin{0.95};

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
  throw std::runtime_error{"acos/bank oracle needs 80-bit long double"};
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

calculation native_asin(calculation const x) {
  return tfx::math::x87::atan2(x, sqrt(calculation{1} - x * x));
}

calculation acos_pi2_asin(calculation const x) {
#if defined(TFX_SOFT_X87)
  return tfx::math::calculation_pi2() - native_asin(x);
#else
  return calculation{std::numbers::pi_v<long double>} / 2 - native_asin(x);
#endif
}

calculation acos_atan2(calculation const x) {
  return tfx::math::x87::atan2(sqrt(calculation{1} - x * x), x);
}

void emit(char const *const label, double const arg_host) {
  calculation const arg{arg_host};
  calculation const asin_v{native_asin(arg)};
  calculation const asin_sqrt{sqrt(calculation{1} - arg * arg)};
  calculation const acos_pi2{acos_pi2_asin(arg)};
  calculation const acos_a2{acos_atan2(arg)};
  calculation const mid_pi2{acos_pi2 * bank_margin};
  calculation const mid_a2{acos_a2 * bank_margin};
  double const mid_pi2_dbl{static_cast<double>(acos_pi2 * bank_margin)};
  double const mid_a2_dbl{static_cast<double>(acos_a2 * bank_margin)};
  std::cout << label
            << " arg=" << dump80(arg)
            << " asin=" << dump80(asin_v)
            << " asin_sqrt=" << dump80(asin_sqrt)
            << " acos_pi2=" << dump80(acos_pi2)
            << " acos_atan2=" << dump80(acos_a2)
            << " mid_pi2=" << dump80(mid_pi2)
            << " mid_atan2=" << dump80(mid_a2)
            << " mid_pi2_dbl=" << dump64(mid_pi2_dbl)
            << " mid_atan2_dbl=" << dump64(mid_a2_dbl)
            << '\n';
}

} // namespace

int main() try {
#if !defined(TFX_SOFT_X87) && !((defined(__i386__) || defined(__x86_64__)) && (LDBL_MANT_DIG == 64))
  std::cout << "SKIP: acos/bank oracle needs hardware x87 or SoftFloat\n";
  return 77;
#else
  tfx::math::floating_environment const environment;

  // Guidance trajectory lift-ratio samples that previously exposed SoftFloat
  // vs hardware bank ULP gaps (case 4 / 7 / 12-style magnitudes).
  std::vector<std::pair<char const *, double>> const samples{
    {"guid_c4", 0x1.6169e46411c37p-3},
    {"guid_c7", 0x1.ea76a0f81b586p-4},
    {"guid_c12", 0x1.8c3a68c4ccfb4p-3},
    {"guid_c38", 0x1.183197aeb4ae7p-3},
    {"guid_c46", 0x1.4dd3ec357249cp-3},
  };
  for(auto const &[label, arg] : samples) emit(label, arg);

  // Dense grid through the positive bank acos domain.
  for(int i{1}; i <= 200; ++i) {
    double const arg{i * 0.004}; // (0, 0.8]
    char label[32];
    std::snprintf(label, sizeof label, "grid_%03d", i);
    emit(label, arg);
  }

  return 0;
#endif
} catch(std::exception const &error) {
  std::cerr << error.what() << '\n';
  return 1;
}
