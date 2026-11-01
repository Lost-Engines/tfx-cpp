#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include "math/calculation.h"
#include "math/floating_environment.h"

auto main()->int try {
#if !defined(TFX_SOFT_X87)
  std::cout << "SKIP: SoftFloat arithmetic backend was not enabled for this build" << std::endl;
  return 77;
#else
  auto require = [](bool const condition, char const *const message) {
    if(!condition) throw std::runtime_error{message};
  };
  {
    tfx::math::floating_environment const environment;
    require(extF80_roundingPrecision == 64, "SoftFloat precision is not Watcom double-precision");
    require(softfloat_roundingMode == softfloat_round_near_even, "SoftFloat rounding is not nearest-even");

    // 1 + 2^-53 rounds away under 64-bit significands and back under PC=53.
    tfx::math::float80 const one{1.0};
    tfx::math::float80 const half_ulp{0x1p-53};
    require(static_cast<double>(one + half_ulp) == 1.0, "SoftFloat PC=53 did not round 1+0x1p-53 to 1");

    tfx::math::float80 const a{100.0};
    tfx::math::float80 const b{0.25};
    require(static_cast<double>(a + b) == 100.25, "SoftFloat add differs");
    require(static_cast<double>(a * b) == 25.0, "SoftFloat mul differs");
  }
  require(std::numeric_limits<tfx::math::calculation>::digits == 64, "calculation type is not x87-width");
  std::cout << "SoftFloat Watcom-precision arithmetic checks passed" << std::endl;
  return EXIT_SUCCESS;
#endif
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
