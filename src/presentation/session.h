#pragma once

#include <memory>
#include "presentation/player.h"
#include "presentation/runtime.h"
#include "resources/archive.h"

namespace tfx::presentation {

class session {
private:
  struct frame {
    program graph;
    runtime execution;
    frame(resources::bytes const &bytes, variables &state, std::string_view function);
  };
  resources::archive const &game;
  fonts const &font_data;
  dac_palette text_palette;
  variables &state;
  std::string language;
  std::vector<std::unique_ptr<frame>> stack;
  std::unique_ptr<scene_player> scene;
  render::framebuffer display;
  dac_palette current_palette;
  dac_palette displayed_colours{};
  sequence_controls sequence;
  bool node_start{true};
  void load(std::string const &name, std::string_view function);

public:
  session(resources::archive const &game, fonts const &fonts, dac_palette const &text_palette,
    variables &state, std::string const &program, std::string_view function = {}, std::string language = "english");
  // Run until a visual frame or an explicit menu/flight/planner host action is ready.
  statement const *advance(scene_counters counters, scene_input &input);
  statement const *pending() const;
  void complete();
  bool finished() const;
  render::framebuffer const &image() const;
  render::palette colours() const;
  std::string const &function_name() const;
};

} // namespace tfx::presentation
