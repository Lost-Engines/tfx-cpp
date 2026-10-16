#pragma once

#include <functional>
#include <limits>
#include "presentation/fonts.h"
#include "presentation/program.h"

namespace tfx::presentation {

struct text_line {
  std::string text;
  vec2<int16_t> position;
  int16_t width;
};
struct prepared_text {
  std::vector<text_line> lines;
  uint16_t characters{0};
  font_id font;
  uint8_t colour;
  bool shadow;
};
using text_counter = uint32_t;
struct reveal_progress {
  text_counter previous;
  uint16_t visible{0};
  uint16_t remainder{0};
};
class text_reveal {
private:
  uint16_t total;
  reveal_progress progress;

public:
  text_reveal(uint16_t characters, text_counter initial_counter);
  bool advance(text_counter counter, bool skip);
  reveal_progress const &state() const;
};
using external_text = std::function<std::string(std::string_view)>;
prepared_text prepare_text(text_block const &source, variables const &state, fonts const &fonts, external_text resolve = {});
void draw_text(render::framebuffer &target, prepared_text const &text, fonts const &fonts, unsigned int characters = std::numeric_limits<unsigned int>::max(), render::framebuffer *coverage = nullptr);

} // namespace tfx::presentation
