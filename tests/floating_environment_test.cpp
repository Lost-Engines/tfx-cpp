#include <iostream>
#include <stdexcept>
#include "math/floating_environment.h"

namespace {

unsigned short control_word() {
#if (defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__)
  unsigned short result;
  __asm__ volatile("fnstcw %0" : "=m"(result));
  return result;
#else
  return 0;
#endif
}
void require(bool const condition, char const *const message) {
  if(!condition) throw std::runtime_error{message};
}

} // anonymous namespace

int main() try {
#if !((defined(__i386__) || defined(__x86_64__)) && defined(__GNUC__))
  return 77;
#endif
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
} catch(std::exception const &error) { std::cerr << error.what() << '\n'; return 1; }
