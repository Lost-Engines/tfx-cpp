#include <array>
#include <cstring>
#include <limits>
#include "math/x87.h"

static_assert(sizeof(long double) >= 10 && std::numeric_limits<long double>::digits == 64);

// This test-only adapter replaces Unicorn's double-precision FPATAN fallback
// with a host instruction. The game never loads this shared library.
extern "C" void tfx_fpatan(unsigned char const *const y_bytes, unsigned char const *const x_bytes, unsigned char *const output, unsigned short const control) {
  long double y{0},x{0};
  std::memcpy(&y,y_bytes,10);
  std::memcpy(&x,x_bytes,10);
  unsigned short previous;
  __asm__ volatile("fnstcw %0" : "=m"(previous));
  __asm__ volatile("fldcw %0" : : "m"(control));
  auto const result{tfx::math::x87::atan2(y,x)};
  std::memcpy(output,&result,10);
  __asm__ volatile("fldcw %0" : : "m"(previous));
}

extern "C" void tfx_sine_cosine(unsigned char const *const input, unsigned char *const output, unsigned short const control, unsigned int const cosine) {
  long double value{0};
  std::memcpy(&value,input,10);
  unsigned short previous;
  __asm__ volatile("fnstcw %0" : "=m"(previous));
  __asm__ volatile("fldcw %0" : : "m"(control));
  auto const result{cosine ? tfx::math::x87::cos(value) : tfx::math::x87::sin(value)};
  std::memcpy(output,&result,10);
  __asm__ volatile("fldcw %0" : : "m"(previous));
}

extern "C" void tfx_tangent(unsigned char const *const input, unsigned char *const output, unsigned short const control) {
  long double value{0};
  std::memcpy(&value,input,10);
  unsigned short previous;
  __asm__ volatile("fnstcw %0" : "=m"(previous));
  __asm__ volatile("fldcw %0" : : "m"(control));
  auto const result{tfx::math::x87::tan(value)};
  std::memcpy(output,&result,10);
  __asm__ volatile("fldcw %0" : : "m"(previous));
}
