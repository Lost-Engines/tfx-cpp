#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include "missions/initialisation.h"
#include "platform/window.h"
#include "render/camera.h"
#include "render/framebuffer.h"
#include "render/software_renderer.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "world/assets.h"
#include "world/environment.h"
#include "world/scene.h"

namespace {

unsigned int number(std::string_view const text) {
  unsigned int result{0};
  auto const [end,error]{std::from_chars(text.data(),text.data() + text.size(),result)};
  if(error != std::errc{} || end != text.data() + text.size()) throw std::runtime_error{"expected a non-negative integer: " + std::string{text}};
  return result;
}

} // anonymous namespace

auto main(int const argc, char const *const argv[])->int try {
  /// Load an original mission scene; the camera controls below are developer inspection, not aircraft flight physics
  std::filesystem::path data_directory{"."};
  std::string mission_name{"miss830"}, override_environment, override_grid;
  unsigned int scale{0}, scene_radius{6}, frame_limit{0};
  std::optional<vec2<unsigned int>> override_cell;
  std::optional<std::filesystem::path> screenshot;
  for(int i{1}; i != argc; ++i) {
    std::string_view const argument{argv[i]};
    auto const equals{argument.find('=')};
    auto const key{argument.substr(0,equals)};
    auto const value{[&]()->std::string_view {
      if(equals != std::string_view::npos) return argument.substr(equals + 1);
      if(i + 1 == argc) throw std::runtime_error{"missing value for " + std::string{key}};
      return argv[++i];
    }};
    if(key == "--help") {
      std::cout << "TFX C++ — early native scene reconstruction\n"
                   "Usage: tfx --data-dir DIRECTORY [--mission 830] [--scale N]\n"
                   "  --data-dir DIRECTORY  Original TFX 2.05 installation (DID.DAT and TFX.DAT)\n"
                   "  --mission N           Select a mission scene (default 830)\n"
                   "  --scale N             Window scale; 0 selects the largest fitting scale (default)\n"
                   "\nScene inspection: WASD moves, R/F rises/descends, arrows or right-drag look, Shift moves faster, Escape exits.\n"
                   "Player flight physics, mission execution and audio are not implemented yet.\n";
#ifndef NDEBUG
      std::cout << "\nDeveloper options:\n"
                   "  --environment NAME    Override mission lighting/weather\n"
                   "  --grid NAME           Inspect an alternate stored terrain grid\n"
                   "  --cell X,Z            Inspect a particular terrain cell\n"
                   "  --scene-radius N      Inspection neighbourhood in tiles (default 6)\n"
                   "  --screenshot FILE     Save the initial scene as a PPM image without opening a window\n"
                   "  --frames N            Exit the window after N frames (0 is unlimited)\n";
#endif // NDEBUG
      return EXIT_SUCCESS;
    }
    if(key == "--data-dir") data_directory = value();
    else if(key == "--mission") {
      auto const selected{value()};
      mission_name = "miss" + std::to_string(number(selected));
    } else if(key == "--scale") {
      scale = number(value());
      if(scale > 16) throw std::runtime_error{"window scale must be between 0 (automatic) and 16"};
    }
#ifndef NDEBUG
    else if(key == "--environment") override_environment = value();
    else if(key == "--grid") override_grid = value();
    else if(key == "--cell") {
      auto const cell{value()};
      auto const comma{cell.find(',')};
      if(comma == std::string_view::npos) throw std::runtime_error{"--cell expects X,Z"};
      override_cell = vec2<unsigned int>{number(cell.substr(0,comma)),number(cell.substr(comma + 1))};
      if(override_cell->x >= tfx::world::map_width || override_cell->y >= tfx::world::map_height) throw std::runtime_error{"cell must lie within 0..199 on each axis"};
    } else if(key == "--scene-radius") {
      scene_radius = number(value());
      if(scene_radius < 1 || scene_radius > 20) throw std::runtime_error{"scene radius must be between 1 and 20 tiles"};
    } else if(key == "--screenshot") screenshot = value();
    else if(key == "--frames") frame_limit = number(value());
#endif // NDEBUG
    else throw std::runtime_error{"unrecognised option: " + std::string{key} + "; use --help"};
  }
  auto const archive_path{tfx::resources::find_game_archive(data_directory)};
  tfx::resources::archive const game{archive_path};
  tfx::resources::executable_tables const tables{archive_path.parent_path() / "TFX.DAT"};
  tfx::world::mission const selected{game,mission_name};
  auto const mission_setup{tfx::missions::initialise(selected.script)};
  tfx::world::environment const environment{game,override_grid.empty() ? selected.grid_name() : override_grid,override_environment.empty() ? mission_setup.environment : override_environment};
  auto const colours{tfx::render::decode_palette(game.read("colours/" + environment.palette_name + ".col"))};
  tfx::world::assets assets{game};
  tfx::world::scene scene{environment,assets};
  tfx::render::software_renderer renderer{tables};
  vec3d position{mission_setup.start.position};
  if(mission_setup.start.landed) position.y = -300;                                  // elevated inspection view; not a player ground-contact calculation
  double heading{0}, pitch{-.12};
  if(override_cell) {
    position = vec3d{(override_cell->x + .5) * tfx::world::cell_units,-1800,(override_cell->y + .5) * tfx::world::cell_units};
    pitch = -.35;
  }
  auto const draw{[&]{
    auto view{tfx::render::inspection_camera(position,heading,pitch)};
    view.far_distance = scene_radius * tfx::world::cell_units;
    renderer.background(view,0,32);
    scene.draw(renderer,view,scene_radius);
  }};
  draw();
  std::cout << "TFX " << mission_name << " / " << environment.name << " / " << environment.lighting_name << ": " << scene.parts_drawn << " model parts, " << scene.primitives_drawn << " drawing primitives" << std::endl;
  if(!scene.warnings.empty()) {
    unsigned int printed{0};
    for(auto const &warning : scene.warnings) if(printed++ < 6) std::cerr << "Preview note: " << warning << std::endl;
    if(scene.warnings.size() > 6) std::cerr << "Preview notes: " << scene.warnings.size() << " distinct limitations; this is a scene-inspection build" << std::endl;
  }
  if(screenshot) {
    renderer.output.screenshot(*screenshot,colours);
    std::cout << "Initial scene screenshot: " << *screenshot << std::endl;
    return EXIT_SUCCESS;
  }
  tfx::platform::window window{scale};
  // Wayland maps the window after its first buffer: present before waiting for focus.
  window.present(renderer.output.colourise(colours));
  auto *const host{window.get()};
  double previous_time{glfwGetTime()}, title_time{previous_time}, last_mouse_x{0}, last_mouse_y{0}, timer_fraction{0};
  unsigned int frames{0}, interval_frames{0};
  bool captured{false}, mouse_started{false};
  while(window.poll()) {
    double const now{glfwGetTime()}, real_elapsed{now - previous_time}, elapsed{std::clamp(real_elapsed,0.0,.1)};
    previous_time = now;
    if(!window.focused()) {
      captured = false;
      mouse_started = false;
      glfwWaitEventsTimeout(.05);
      continue;
    }
    auto const down{[host](int const key){ return glfwGetKey(host,key) == GLFW_PRESS; }};
    if(down(GLFW_KEY_ESCAPE)) break;
    bool const capture{glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS};
    if(capture != captured) {
      captured = capture;
      mouse_started = false;
      glfwSetInputMode(host,GLFW_CURSOR,captured ? GLFW_CURSOR_DISABLED : GLFW_CURSOR_NORMAL);
    }
    if(captured) {
      double mouse_x{0}, mouse_y{0};
      glfwGetCursorPos(host,&mouse_x,&mouse_y);
      if(mouse_started) { heading += (mouse_x - last_mouse_x) * .004; pitch -= (mouse_y - last_mouse_y) * .004; }
      last_mouse_x = mouse_x;
      last_mouse_y = mouse_y;
      mouse_started = true;
    }
    heading += (down(GLFW_KEY_RIGHT) - down(GLFW_KEY_LEFT)) * elapsed;
    pitch += (down(GLFW_KEY_UP) - down(GLFW_KEY_DOWN)) * elapsed;
    pitch = std::clamp(pitch,-1.5,1.5);
    auto const camera{tfx::render::inspection_camera(position,heading,pitch)};
    double const movement{1500 * elapsed * (down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT) ? 6 : 1)};
    position += camera.forward * ((down(GLFW_KEY_W) - down(GLFW_KEY_S)) * movement);
    position += camera.right * ((down(GLFW_KEY_D) - down(GLFW_KEY_A)) * movement);
    position.y += (down(GLFW_KEY_F) - down(GLFW_KEY_R)) * movement;
    timer_fraction += real_elapsed * tfx::world::timer_hz;
    auto const timer_step{static_cast<uint64_t>(std::floor(timer_fraction))};
    timer_fraction -= static_cast<double>(timer_step);
    scene.advance(static_cast<tfx::world::timer_ticks>(timer_step));
    draw();
    window.present(renderer.output.colourise(colours));
    ++frames;
    ++interval_frames;
    if(now - title_time >= .5) {
      window.title("TFX C++ — scene inspection — " + mission_name + " / " + environment.name + " / " + environment.lighting_name + " — " + std::to_string(static_cast<int>(interval_frames / (now - title_time))) + " fps");
      title_time = now;
      interval_frames = 0;
    }
    if(frame_limit && frames >= frame_limit) break;
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
