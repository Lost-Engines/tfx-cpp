#include <algorithm>
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <format>
#include <iostream>
#include <numbers>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include "platform/flight.h"
#include "platform/presentations.h"
#include "world/environment.h"

namespace {

unsigned int number(std::string_view const text) {
  unsigned int result{0};
  auto const [end,error]{std::from_chars(text.data(),text.data() + text.size(),result)};
  if(error != std::errc{} || end != text.data() + text.size()) throw std::runtime_error{"expected a non-negative integer: " + std::string{text}};
  return result;
}

} // anonymous namespace

auto main(int const argc, char const *const argv[])->int try {
  std::filesystem::path data_directory{"."};
  std::string mission_name{"miss501"}, override_environment, override_grid;
  unsigned int scale{0}, scene_radius{6}, frame_limit{0}, flight_steps{0};
  bool inspect{false}, direct_mission{false}, skip_intro{false};
  std::string presentation, presentation_function, language{"english"};
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
                   "  --mission N           Enter a mission directly instead of the original front end\n"
                   "  --skip-intro          Start at pilot enrolment without the opening sequence\n"
                   "  --language NAME       english, french, german, spanish or italian\n"
                   "  --scale N             Window scale; 0 selects the largest fitting scale (default)\n"
                   "\nArcade flight: mouse or arrows steer; hold left/right mouse or =/- for thrust.\n"
                   "[ and ] toggle engines; G gear; W wheel brakes; B air brakes; Alt+B brake chute; Shift+B cut away.\n"
                   "Enter selects air-to-air weapons; Backspace/O air-to-ground; F selects cannon/navigation.\n"
                   "C cycles radar/emitter targets; Z opens/locks laser designator; arrows aim; comma/period zoom.\n"
                   "X clears targets; F1 returns to flight view; Space fires; P pauses; Escape exits.\n"
                   "1/2/3 cycle the MFDs; R changes radar range; N selects the ground-target preview.\n"
                   "This is a flight integration build; combat, campaign flow and audio are still in progress.\n";
#ifndef NDEBUG
      std::cout << "\nDeveloper options:\n"
                   "  --menu NAME            Run an original options menu\n"
                   "  --presentation NAME[:FUNCTION]  Play an original presentation graph\n"
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
    else if(key == "--language") {
      language = value();
      std::array<std::string_view,5> constexpr languages{"english","french","german","spanish","italian"};
      if(std::ranges::find(languages,language) == languages.end()) throw std::runtime_error{"unknown TFX language: " + language};
    }
    else if(key == "--skip-intro") skip_intro = true;
    else if(key == "--mission") {
      direct_mission = true;
      auto const selected{value()};
      mission_name = "miss" + std::to_string(number(selected));
    } else if(key == "--scale") {
      scale = number(value());
      if(scale > 16) throw std::runtime_error{"window scale must be between 0 (automatic) and 16"};
    }
#ifndef NDEBUG
    else if(key == "--menu") presentation = "menu:" + std::string{value()};
    else if(key == "--presentation") {
      auto const selection{value()};
      auto const colon{selection.find(':')};
      presentation = selection.substr(0,colon);
      if(colon != std::string_view::npos) presentation_function = selection.substr(colon + 1);
    }
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
  if(!presentation.empty()) {
    tfx::platform::play_presentation(game,tables,presentation,presentation_function,language,scale,frame_limit,screenshot);
    return EXIT_SUCCESS;
  }
  tfx::platform::flight_options const flight{
    .mission{mission_name},
    .environment{override_environment},
    .grid{override_grid},
    .cell{override_cell ? std::optional<vec2<unsigned int>>{std::in_place,*override_cell} : std::nullopt},
    .screenshot{screenshot},
    .scale{scale},
    .scene_radius{scene_radius},
    .frame_limit{frame_limit},
    .flight_steps{flight_steps},
    .inspect{inspect},
  };
  if(direct_mission || inspect || flight_steps || !override_environment.empty() || !override_grid.empty()) {
    tfx::missions::variables campaign;
    tfx::platform::fly_mission(game,tables,flight,campaign);
  } else tfx::platform::play_game(game,tables,archive_path.parent_path(),language,skip_intro,flight);
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
