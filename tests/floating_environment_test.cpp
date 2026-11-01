#include <iostream>
#include <stdexcept>
#include "math/floating_environment.h"

namespace {

#if defined(TFX_SOFT_X87)
std::uint_fast8_t rounding_mode() { return softfloat_roundingMode; }
std::uint_fast8_t precision_mode() { return extF80_roundingPrecision; }
#elif (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
unsigned short control_word() {
  unsigned short result;
  __asm__ volatile("fnstcw %0" : "=m"(result));
  return result;
}
#endif

void require(bool const condition, char const *const message) {
  if(!condition) throw std::runtime_error{message};
}

} // anonymous namespace

int main() try {
#if defined(TFX_SOFT_X87)
  auto const previous_rounding{rounding_mode()};
  auto const previous_precision{precision_mode()};
  {
    tfx::math::floating_environment const environment;
    require(rounding_mode() == softfloat_round_near_even, "SoftFloat rounding differs");
    require(precision_mode() == 64, "SoftFloat precision differs");
    {
      tfx::math::floating_environment const nested;
      require(rounding_mode() == softfloat_round_near_even, "nested SoftFloat rounding differs");
      require(precision_mode() == 64, "nested SoftFloat precision differs");
    }
    require(rounding_mode() == softfloat_round_near_even, "nested SoftFloat scope changed outer rounding");
    require(precision_mode() == 64, "nested SoftFloat scope changed outer precision");
  }
  require(rounding_mode() == previous_rounding, "SoftFloat scope leaked rounding to the host");
  require(precision_mode() == previous_precision, "SoftFloat scope leaked precision to the host");
  try {
    tfx::math::floating_environment const environment;
    throw 1;
  } catch(int) {}
  require(rounding_mode() == previous_rounding, "exception did not restore SoftFloat rounding");
  require(precision_mode() == previous_precision, "exception did not restore SoftFloat precision");
  std::cout << "SoftFloat arithmetic precision, nested scopes and exception restoration agree\n";
  return 0;
#elif (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  auto const previous{control_word()};
  {
    tfx::math::floating_environment const environment;
    require(control_word() == 0x127f,"native precision/rounding control differs");
    volatile long double one{1.0L}, half_ulp{0x1p-53L};
    long double const rounded{one + half_ulp};
    require(rounded == 1.0L,"native arithmetic does not round at 53 bits");
    {
      tfx::math::floating_environment const nested;
      require(control_word() == 0x127f,"nested precision scope differs");
    }
    require(control_word() == 0x127f,"nested scope changed the outer precision");
  }
  require(control_word() == previous,"native scope leaked its control word to the host");
  try {
    tfx::math::floating_environment const environment;
    throw 1;
  } catch(int) {}
  require(control_word() == previous,"exception did not restore host precision");
  std::cout << "Native arithmetic precision, nested scopes and exception restoration agree\n";
  return 0;
#else
  return 77;
#endif
} catch(std::exception const &error) { std::cerr << error.what() << '\n'; return 1; }
