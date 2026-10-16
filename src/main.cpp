#include <algorithm>
#include <array>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include "missions/initialisation.h"
#include "flight/arcade.h"
#include "actors/program.h"
#include "actors/surface.h"
#include "simulation/timing.h"
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
  /// Direct mission entry; campaign/menu dispatch will eventually supply this same initial state
  std::filesystem::path data_directory{"."};
  std::string mission_name{"miss501"}, override_environment, override_grid;
  unsigned int scale{0}, scene_radius{6}, frame_limit{0}, flight_steps{0};
  bool inspect{false};
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
      std::cout << "TFX C++ — native flight reconstruction\n"
                   "Usage: tfx --data-dir DIRECTORY [--mission 501] [--scale N]\n"
                   "  --data-dir DIRECTORY  Original TFX 2.05 installation (DID.DAT and TFX.DAT)\n"
                   "  --mission N           Select a mission (default 501, first FWS engagement)\n"
                   "  --scale N             Window scale; 0 selects the largest fitting scale (default)\n"
                   "\nArcade flight: mouse or arrows steer; hold left/right mouse or =/- for thrust.\n"
                   "[ and ] toggle engines; G gear; W wheel brakes; B air brakes; Alt+B brake chute; Shift+B cut away.\n"
                   "P pauses; Escape exits.\n"
                   "This is a flight integration build; combat, campaign flow and audio are still in progress.\n";
#ifndef NDEBUG
      std::cout << "\nDeveloper options:\n"
                   "  --inspect             Free scene camera: WASD, R/F, arrows/right-drag, Shift\n"
                   "  --flight-steps N      Advance N four-tick flight steps before initial capture\n"
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
    else if(key == "--inspect") inspect = true;
    else if(key == "--flight-steps") flight_steps = number(value());
    else if(key == "--environment") override_environment = value();
    else if(key == "--grid") override_grid = value();
    else if(key == "--cell") {
      auto const cell{value()};
      auto const comma{cell.find(',')};
      if(comma == std::string_view::npos) throw std::runtime_error{"--cell expects X,Z"};
      inspect = true;
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
  auto const profiles{tfx::actors::profiles(game.read("waybin/craftype.cfg"))};
  tfx::actors::program const actor_program{game.read("waybin/" + mission_setup.waypoints + ".way")};
  auto const actors{tfx::actors::initialise(actor_program,profiles,tables.formations)};
  struct surface_actor {
    tfx::actors::surface_state state;
    tfx::world::scene_handle visual;
    tfx::actors::profile const *profile;
  };
  std::vector<surface_actor> surface_actors;
  std::string radio_message;
  int radio_ticks{0};
  for(auto const &actor : actors) {
    auto const profile{std::ranges::find(profiles,actor.profile_id,&tfx::actors::profile::id)};
    auto const visual{scene.create_actor(profile->definition,vec3d{actor.position} / tfx::actors::position_unit,actor.angles)};
    if(actor.kind == tfx::actors::record_kind::surface) surface_actors.push_back({
      .state{tfx::actors::create_surface(actor,actor_program)},
      .visual{visual},
      .profile{&*profile},
    });
  }
  auto const advance_actors{[&](unsigned int const ticks){
    // Native 0x75784 visits each actor once per elapsed tick, preserving pool order.
    for(unsigned int tick{0}; tick != std::max(1u,ticks); ++tick) {
      for(auto &actor : surface_actors) {
        for(auto const &request : tfx::actors::advance_surface(actor.state,*actor.profile)) {
          if(request.kind == tfx::actors::surface_request_kind::radio) {
            radio_message = request.text;
            radio_ticks = 5 * 55;
          }
        }
      }
      if(radio_ticks > 0) --radio_ticks;
    }
    for(auto const &actor : surface_actors) scene.place_actor(actor.visual,vec3d{actor.state.pose.position} / tfx::actors::position_unit,actor.state.pose.angles);
  }};
  tfx::render::software_renderer renderer{tables};
  tfx::flight::arcade_state player;
  player.aircraft = mission_setup.aircraft;
  // The native ground-start fallback is zero for type 50, -20 otherwise (0x8c318).
  auto const start_x{static_cast<unsigned int>(std::clamp(mission_setup.start.position.x / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_width) - 1))};
  auto const start_z{static_cast<unsigned int>(std::clamp(mission_setup.start.position.z / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_height) - 1))};
  auto const flags{assets.object(environment.variant(start_x,start_z)).flags};
  tfx::flight::ground_contact ground{
    .present{true},
    .height{static_cast<int16_t>(mission_setup.start.landed && (!(flags & 2) || (flags & 255) >> 2 != 50) ? -20 : 0)},
  };
  auto const initial_ground{ground};
  auto const restart{[&]{
    ground = initial_ground;
    player = {};
    player.aircraft = mission_setup.aircraft;
    tfx::flight::initialise_arcade(player,mission_setup.start.position,mission_setup.angles,mission_setup.speed_factor,mission_setup.start.landed,ground);
  }};
  auto const advance_world{[&](tfx::flight::flight_controls const &controls, tfx::simulation::timer_ticks const elapsed) {
    bool const flying{!player.collision};
    auto const previous{vec3<int32_t>{player.integer_position}};
    if(flying) tfx::flight::advance_arcade(player,controls,elapsed,ground);
    advance_actors(elapsed);
    if(flying) {
      // Native 0x72018 updates actors before collecting contacts; the next flight frame consumes this surface result.
      auto const contact{scene.collide_terrain(previous,player.integer_position)};
      ground = {
        .present{contact.surface_present},
        .height{contact.surface_height},
      };
      if(contact.collisions && player.crashing) player.collision = 1;
    }
    scene.advance(elapsed);
  }};
  if(!inspect || flight_steps) restart();
  for(unsigned int step{0}; step != flight_steps; ++step) advance_world({},4);
  vec3d position{mission_setup.start.position};
  if(mission_setup.start.landed) position.y = -300;
  double heading{0}, pitch{-.12};
  if(override_cell) {
    inspect = true;
    position = vec3d{(override_cell->x + .5) * tfx::world::cell_units,-1800,(override_cell->y + .5) * tfx::world::cell_units};
    pitch = -.35;
  }
  bool paused{false};
  auto const draw{[&]{
    auto view{inspect ? tfx::render::inspection_camera(position,heading,pitch) : tfx::render::aircraft_camera(player.position,player.orientation)};
    view.far_distance = scene_radius * tfx::world::cell_units;
    renderer.background(view,0,32);
    scene.draw(renderer,view,scene_radius);
    if(!inspect) {
      // Readouts use the original miniature font; full native HUD layout/MFDs are still being connected.
      uint8_t constexpr hud_colour{15};
      renderer.text(5,5,std::format("MACH {:.2f}  ALT {} FT",player.speed_mach,static_cast<int>(-player.position.y * tfx::flight::feet_per_world_unit)),hud_colour);
      renderer.text(5,14,std::format("THR {}  FUEL {}  AB {}",static_cast<int>(player.throttle * 100),static_cast<int>(player.fuel),player.afterburner),hud_colour);
      renderer.text(5,185,std::string{player.gear_down ? "GEAR DOWN  " : "GEAR UP  "} + (player.left_engine ? "L ON  " : "L OFF  ") + (player.right_engine ? "R ON" : "R OFF"),hud_colour);
      renderer.text(245,5,"ARCADE",hud_colour);
      if(paused) renderer.text(140,80,"PAUSED",hud_colour);
      if(player.collision) renderer.text(120,92,"COLLISION",hud_colour);
      if(radio_ticks > 0) renderer.text(5,170,radio_message,hud_colour);
    }
  }};
  draw();
  std::cout << "TFX " << mission_name << " / " << environment.name << " / " << environment.lighting_name << ": " << scene.parts_drawn << " model parts, " << scene.primitives_drawn << " drawing primitives" << std::endl;
  if(!scene.warnings.empty()) {
    unsigned int printed{0};
    for(auto const &warning : scene.warnings) if(printed++ < 6) std::cerr << "Preview note: " << warning << std::endl;
    if(scene.warnings.size() > 6) std::cerr << "Preview notes: " << scene.warnings.size() << " distinct limitations; this is a flight-integration build" << std::endl;
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
  std::array<bool,GLFW_KEY_LAST + 1> held{false};
  tfx::simulation::timer_counter counter{0};
  tfx::simulation::flight_clock flight_clock{counter};
  flight_clock.begin({});
  double pitch_input{0}, roll_input{0};
  while(window.poll()) {
    double const now{glfwGetTime()}, real_elapsed{now - previous_time}, elapsed{std::clamp(real_elapsed,0.0,.1)};
    previous_time = now;
    if(!window.focused()) {
      captured = false;
      mouse_started = false;
      held.fill(false);
      pitch_input = 0;
      roll_input = 0;
      glfwWaitEventsTimeout(.05);
      continue;
    }
    auto const down{[host](int const key){ return glfwGetKey(host,key) == GLFW_PRESS; }};
    if(down(GLFW_KEY_ESCAPE)) break;
    auto const pressed{[&](int const key){
      bool const active{down(key)}, edge{active && !held[static_cast<unsigned int>(key)]};
      held[static_cast<unsigned int>(key)] = active;
      return edge;
    }};
    if(!inspect && pressed(GLFW_KEY_P)) paused = !paused;
    bool const capture{inspect ? glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS : !paused};
    if(capture != captured) {
      captured = capture;
      mouse_started = false;
      glfwSetInputMode(host,GLFW_CURSOR,captured ? GLFW_CURSOR_DISABLED : GLFW_CURSOR_NORMAL);
    }
    if(captured) {
      double mouse_x{0}, mouse_y{0};
      glfwGetCursorPos(host,&mouse_x,&mouse_y);
      if(mouse_started) {
        if(inspect) { heading += (mouse_x - last_mouse_x) * .004; pitch -= (mouse_y - last_mouse_y) * .004; }
        else { pitch_input += mouse_y - last_mouse_y; roll_input += mouse_x - last_mouse_x; }
      }
      last_mouse_x = mouse_x;
      last_mouse_y = mouse_y;
      mouse_started = true;
    }
    if(inspect) {
      heading += (down(GLFW_KEY_RIGHT) - down(GLFW_KEY_LEFT)) * elapsed;
      pitch += (down(GLFW_KEY_UP) - down(GLFW_KEY_DOWN)) * elapsed;
      pitch = std::clamp(pitch,-1.5,1.5);
      auto const camera{tfx::render::inspection_camera(position,heading,pitch)};
      double const movement{1500 * elapsed * (down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT) ? 6 : 1)};
      position += camera.forward * ((down(GLFW_KEY_W) - down(GLFW_KEY_S)) * movement);
      position += camera.right * ((down(GLFW_KEY_D) - down(GLFW_KEY_A)) * movement);
      position.y += (down(GLFW_KEY_F) - down(GLFW_KEY_R)) * movement;
      timer_fraction += real_elapsed * tfx::world::timer_hz;
      auto const step{static_cast<uint64_t>(std::floor(timer_fraction))};
      timer_fraction -= static_cast<double>(step);
      scene.advance(static_cast<tfx::world::timer_ticks>(step));
    } else if(!paused) {
      if(!player.collision) {
        if(pressed(GLFW_KEY_LEFT_BRACKET)) player.left_engine = !player.left_engine;
        if(pressed(GLFW_KEY_RIGHT_BRACKET)) player.right_engine = !player.right_engine;
        if(!player.left_engine && !player.right_engine) player.afterburner = 0;
        if(pressed(GLFW_KEY_G) && !player.landed && !(player.aircraft == tfx::flight::player_aircraft::eurofighter && !player.gear_down && player.fixed_speed > 350)) player.gear_down = !player.gear_down;
        if(pressed(GLFW_KEY_W) && player.landed) player.wheel_brake = !player.wheel_brake;
        if(pressed(GLFW_KEY_B)) {
          if(down(GLFW_KEY_LEFT_ALT) || down(GLFW_KEY_RIGHT_ALT)) {
            if(player.aircraft != tfx::flight::player_aircraft::raptor && !player.brake_chute_cut_away && player.fixed_speed >= 20) player.brake_chute = true;
          } else if(down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT)) {
            if(player.aircraft != tfx::flight::player_aircraft::raptor && player.brake_chute) { player.brake_chute = false; player.brake_chute_cut_away = true; }
          } else player.air_brake = !player.air_brake;
        }
      }
      timer_fraction += real_elapsed * tfx::simulation::timer_hz;
      auto const ticks{static_cast<tfx::simulation::timer_counter>(std::floor(timer_fraction))};
      timer_fraction -= ticks;
      counter += ticks;
      auto const step{flight_clock.poll(counter)};
      if(step) {
        // Keyboard supplies a relative stick input until the full native device adapter is restored.
        pitch_input += (down(GLFW_KEY_UP) - down(GLFW_KEY_DOWN)) * step->world_ticks * 4;
        roll_input += (down(GLFW_KEY_RIGHT) - down(GLFW_KEY_LEFT)) * step->world_ticks * 4;
        auto const input_word{[](double const value){ return static_cast<int16_t>(std::clamp(value,-32768.0,32767.0)); }};
        tfx::flight::flight_controls const controls{
          .pitch_delta{input_word(pitch_input)},
          .roll_delta{input_word(roll_input)},
          .accelerate{down(GLFW_KEY_EQUAL)},
          .decelerate{down(GLFW_KEY_MINUS)},
          .mouse_buttons{static_cast<uint8_t>((glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS ? 1 : 0) | (glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS ? 2 : 0))},
        };
        pitch_input -= controls.pitch_delta;
        roll_input -= controls.roll_delta;
        advance_world(controls,step->world_ticks);
        flight_clock.begin({});
      } else {
        glfwWaitEventsTimeout(.002);
        continue;
      }
    }
    if(paused) glfwWaitEventsTimeout(.01);
    draw();
    window.present(renderer.output.colourise(colours));
    ++frames;
    ++interval_frames;
    if(now - title_time >= .5) {
      window.title(std::string{inspect ? "TFX C++ — scene inspection — " : "TFX C++ — Arcade flight — "} + mission_name + " / " + environment.name + " / " + environment.lighting_name + " — " + std::to_string(static_cast<int>(interval_frames / (now - title_time))) + " fps");
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
