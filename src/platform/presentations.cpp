#include "presentations.h"
#include <cmath>
#include <algorithm>
#include <stdexcept>

namespace tfx::platform {
namespace {
presentation::scene_counters counters(double const seconds) {
  double constexpr pit_hz{1193182}, bios_divisor{65536}, text_divisor{21845};
  auto const wrapped{[](double const value) { return static_cast<uint32_t>(std::fmod(std::floor(value),4294967296.0)); }};
  return {
    .bios{wrapped(seconds * pit_hz / bios_divisor)},
    .text{wrapped(seconds * pit_hz / text_divisor)},
  };
}
struct scene_keys {
  presentation::scene_input input;
  static void key(GLFWwindow *const host, int const key, int const, int const action, int const) {
    if(action != GLFW_PRESS) return;
    auto &input{static_cast<scene_keys*>(glfwGetWindowUserPointer(host))->input};
    // Every make code replaces the last key; unrecognised keys also cancel a latched Escape.
    input.key = key == GLFW_KEY_SPACE ? presentation::scene_key::space : key == GLFW_KEY_ESCAPE ? presentation::scene_key::escape : key == GLFW_KEY_Q ? presentation::scene_key::quit : presentation::scene_key::none;
  }
};
} // anonymous namespace

void play_presentation(resources::archive const &game, resources::executable_tables const &tables,
  std::string const &name, std::string_view const function, std::string const &language,
  unsigned int const scale, unsigned int const frame_limit, std::optional<std::filesystem::path> const &screenshot) {
  presentation::variables state{
    {"pilotname",std::string{"PILOT"}},
    {"firstname",std::string{"TFX"}},
    {"callsign",std::string{"TFX"}},
  };
  // Referenced subtitles in child parsers use the parent's shared variables.
  presentation::program const root{game.read("tfx.par")};
  for(auto const &variable : root.variables) state.try_emplace(variable.name,variable.text ? presentation::variable_value{std::string{}} : presentation::variable_value{uint32_t{0}});
  presentation::session session{game,tables.presentation_fonts(),tables.text_palette,state,name,function,language};
  scene_keys controls;
  unsigned int frames{0};
  auto const step{[&](double const elapsed) {
    auto const *action{session.advance(counters(elapsed),controls.input)};
    // Sound is deferred; do not turn a request into a prerecorded audition.
    while(action && action->kind == presentation::node_kind::audio) {
      session.complete();
      action = session.advance(counters(elapsed),controls.input);
    }
    if(action) throw std::runtime_error{"presentation reached an unfinished host action in " + session.function_name()};
  }};
  if(screenshot) {
    for(unsigned int frame{0}; frame != std::max(1u,frame_limit) && !session.finished(); ++frame) step(frame / 70.0);
    session.image().screenshot(*screenshot,session.colours());
    return;
  }
  window window{scale};
  auto *const host{window.get()};
  glfwSetWindowUserPointer(host,&controls);
  glfwSetKeyCallback(host,scene_keys::key);
  step(0);
  window.present(session.image().colourise(session.colours()));
  double const started{glfwGetTime()};
  double next{started};
  while(window.poll() && !session.finished()) {
    double const now{glfwGetTime()};
    if(!window.focused()) {
      controls.input = {};
      next = now;
      glfwWaitEventsTimeout(.05);
      continue;
    }
    if(now < next) { glfwWaitEventsTimeout(std::min(.01,next - now));continue; }
    next = now + 1.0 / 70;
    controls.input.shift = glfwGetKey(host,GLFW_KEY_LEFT_SHIFT) == GLFW_PRESS || glfwGetKey(host,GLFW_KEY_RIGHT_SHIFT) == GLFW_PRESS;
    controls.input.mouse_buttons = static_cast<uint8_t>((glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS ? 1 : 0) | (glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS ? 2 : 0));
    step(now - started);
    window.title("TFX C++ — " + name + " / " + session.function_name());
    window.present(session.image().colourise(session.colours()));
    if(frame_limit && ++frames >= frame_limit) break;
  }
  glfwSetKeyCallback(host,nullptr);
  glfwSetWindowUserPointer(host,nullptr);
}

} // namespace tfx::platform
