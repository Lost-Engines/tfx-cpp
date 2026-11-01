#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include "math/calculation.h"
#include "math/floating_environment.h"
#include "math/x87.h"

auto main()->int try {
#if !defined(TFX_SOFT_X87)
  std::cout << "SKIP: SoftFloat transcendental backend was not enabled for this build" << std::endl;
  return 77;
#else
  auto require = [](bool const condition, char const *const message) {
    if(!condition) throw std::runtime_error{message};
  };

  tfx::math::floating_environment const environment;
  // Basic domain checks that must hold on every SoftFloat host.
  require(tfx::math::x87::sin(tfx::math::calculation{0}) == 0, "soft sin(0) differs");
  require(tfx::math::x87::cos(tfx::math::calculation{0}) == 1, "soft cos(0) differs");
  require(tfx::math::x87::atan2(tfx::math::calculation{0}, tfx::math::calculation{1}) == 0, "soft atan2(0,1) differs");
  require(tfx::math::x87::atan2(tfx::math::calculation{1}, tfx::math::calculation{0}) > 1, "soft atan2(1,0) not near +pi/2");

#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__) && (LDBL_MANT_DIG == 64)
  auto host_sin = [](long double const value) {
    long double result;
    __asm__("fsin" : "=t"(result) : "0"(value));
    return result;
  };
  auto host_cos = [](long double const value) {
    long double result;
    __asm__("fcos" : "=t"(result) : "0"(value));
    return result;
  };
  auto host_tan = [](long double const value) {
    long double result;
    __asm__("fptan; fstp %%st(0)" : "=t"(result) : "0"(value));
    return result;
  };
  auto host_atan2 = [](long double const y, long double const x) {
    long double result;
    __asm__("fpatan" : "=t"(result) : "0"(x), "u"(y) : "st(1)");
    return result;
  };
  auto same_ext = [](long double const left, long double const right) {
    unsigned char a[10]{}, b[10]{};
    std::memcpy(a, &left, 10);
    std::memcpy(b, &right, 10);
    return std::memcmp(a, b, 10) == 0;
  };
  auto same_double = [](long double const left, long double const right) {
    return static_cast<double>(left) == static_cast<double>(right);
  };
  // Bochs SoftFloat trig is not Intel-microcode bit-exact. Bound relative error
  // in double so game-scale angles stay within ordinary IEEE-754 double noise.
  auto close_rel = [&](long double const left, long double const right, double const tol = 1e-12) {
    if(same_ext(left, right)) return true;
    double const a{static_cast<double>(left)};
    double const b{static_cast<double>(right)};
    double const scale{std::max(1.0, std::max(std::abs(a), std::abs(b)))};
    return std::abs(a - b) <= tol * scale;
  };

  unsigned long long exact_sin{0}, exact_cos{0}, exact_tan{0}, exact_atan{0};
  unsigned long long double_sin{0}, double_cos{0}, double_tan{0}, double_atan{0};
  unsigned long long close_sin{0}, close_cos{0}, close_tan{0}, close_atan{0};
  unsigned long long samples{0}, atan_samples{0};
  for(int i{-2000}; i <= 2000; ++i) {
    long double const host{i * 0.005L}; // [-10, 10]
    auto const soft{tfx::math::calculation{host}};
    ++samples;
    long double const soft_sin{static_cast<long double>(tfx::math::x87::sin(soft))};
    long double const soft_cos{static_cast<long double>(tfx::math::x87::cos(soft))};
    long double const soft_tan{static_cast<long double>(tfx::math::x87::tan(soft))};
    long double const hw_sin{host_sin(host)};
    long double const hw_cos{host_cos(host)};
    long double const hw_tan{host_tan(host)};
    exact_sin += same_ext(soft_sin, hw_sin);
    exact_cos += same_ext(soft_cos, hw_cos);
    exact_tan += same_ext(soft_tan, hw_tan);
    double_sin += same_double(soft_sin, hw_sin);
    double_cos += same_double(soft_cos, hw_cos);
    double_tan += same_double(soft_tan, hw_tan);
    close_sin += close_rel(soft_sin, hw_sin);
    close_cos += close_rel(soft_cos, hw_cos);
    close_tan += close_rel(soft_tan, hw_tan);
  }
  for(int yi{-20}; yi <= 20; ++yi) {
    for(int xi{-20}; xi <= 20; ++xi) {
      if(yi == 0 && xi == 0) continue;
      long double const y{yi * 0.25L}, x{xi * 0.25L};
      ++atan_samples;
      long double const soft_atan{static_cast<long double>(tfx::math::x87::atan2(tfx::math::calculation{y}, tfx::math::calculation{x}))};
      long double const hw_atan{host_atan2(y, x)};
      exact_atan += same_ext(soft_atan, hw_atan);
      double_atan += same_double(soft_atan, hw_atan);
      close_atan += close_rel(soft_atan, hw_atan);
    }
  }
  std::cout << "soft-vs-hardware ext80 exact: sin " << exact_sin << '/' << samples
            << " cos " << exact_cos << '/' << samples
            << " tan " << exact_tan << '/' << samples
            << " atan2 " << exact_atan << '/' << atan_samples << '\n';
  std::cout << "soft-vs-hardware double exact: sin " << double_sin << '/' << samples
            << " cos " << double_cos << '/' << samples
            << " tan " << double_tan << '/' << samples
            << " atan2 " << double_atan << '/' << atan_samples << '\n';
  std::cout << "soft-vs-hardware rel<=1e-12: sin " << close_sin << '/' << samples
            << " cos " << close_cos << '/' << samples
            << " tan " << close_tan << '/' << samples
            << " atan2 " << close_atan << '/' << atan_samples << '\n';
  // Gate on relative double agreement; Bochs is not claimed bit-exact with Intel.
  // Double-exact majorities catch larger regressions while still allowing ULP noise.
  require(close_sin == samples, "soft FSIN relative error above 1e-12");
  require(close_cos == samples, "soft FCOS relative error above 1e-12");
  require(close_tan == samples, "soft FPTAN relative error above 1e-12");
  require(close_atan == atan_samples, "soft FPATAN relative error above 1e-12");
  require(double_sin * 100 >= samples * 99, "soft FSIN double match rate below 99%");
  require(double_cos * 100 >= samples * 99, "soft FCOS double match rate below 99%");
  require(double_atan * 100 >= atan_samples * 90, "soft FPATAN double match rate below 90%");
#endif
  std::cout << "SoftFloat transcendental checks passed" << std::endl;
  return EXIT_SUCCESS;
#endif
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
