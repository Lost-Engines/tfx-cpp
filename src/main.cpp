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
#include "audio/runtime.h"
#include "audio/sc55_synth.h"
#include "platform/audio_output.h"
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
  std::optional<std::filesystem::path> rom_directory;
  std::optional<uint8_t> music_override;
  tfx::audio::sound_canvas_model canvas_model{tfx::audio::sound_canvas_model::scc1a};
  std::string mission_name{"miss501"}, override_environment, override_grid;
  unsigned int scale{0}, scene_radius{6}, frame_limit{0}, flight_steps{0};
  tfx::simulation::flight_model model{tfx::simulation::flight_model::arcade};
  bool inspect{false}, direct_mission{false}, skip_intro{false}, model_selected{false}, language_selected{false};
  std::optional<tfx::flight::control_source> control_override;
  std::optional<unsigned int> joystick;
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
                   "  --flight-model NAME   arcade, simple, military-spec or realistic; overrides TFX.CFG\n"
                   "  --control NAME        keyboard, mouse or joystick; overrides TFX.CFG\n"
                   "  --joystick N          Select joystick 0..15 (default: first available); enables joystick input\n"
                   "  --music NAME          none, soundblaster-fm, roland-lapc, roland-scc1a or roland-sc55\n"
                   "  --rom-dir DIRECTORY   Roland control/PCM ROMs (default: game directory)\n"
                   "  --scale N             Window scale; 0 selects the largest fitting scale (default)\n"
                   "\nFlight: hold left/right mouse or =/- for thrust.\n"
                   "Arcade uses mouse/arrow steering; other models use the original arrow-key controls.\n"
                   "Keypad * raises afterburner; Alt+keypad * or keypad - lowers it.\n"
                   "[ and ] toggle engines; G gear; H arrestor hook; W wheel brakes; B air brakes; Alt+B brake chute; Shift+B cut away.\n"
                   "E/S toggle ECM/stealth on F-117/F-22; Insert releases chaff; Delete releases a flare.\n"
                   "Enter selects air-to-air weapons; Backspace/O air-to-ground; F selects cannon/navigation.\n"
                   "C cycles radar/emitter targets; Z opens/locks laser designator; arrows aim; comma/period zoom.\n"
                   "X clears targets; F1 returns to flight view; Space fires; P pauses; backtick opens configuration; double Escape ejects; Shift+Q quits.\n"
                   "1/2/3 cycle the MFDs; R changes radar range; N selects the ground-target preview.\n"
                   "Shift+N toggles infrared night vision; Y/U adjust HUD brightness; apostrophe opens/closes the refuelling hookup.\n"
                   "I or backslash toggles ILS; Alt+L requests automatic landing.\n"
                   "A toggles autopilot; 7/8/9/0 choose waypoint/heading/track/speed hold; arrows adjust targets.\n"
                   "5 toggles stick pressure; 6 selects cruise speed; Tab toggles recovery.\n"
                   "Page Up/Down raise and lower the cockpit; Shift+arrows turn the view.\n"
                   "F1 cockpit; Shift+F1 full forward; F2/F3 look left/right; F4 rear; F5 chase.\n"
                   "F6 fly-past; F7 tactical; F8 fired-store camera (twice: nose view).\n"
                   "F9 target observer; F10 virtual cockpit/target tracking.\n"
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
    else if(key == "--rom-dir") rom_directory = value();
    else if(key == "--music") {
      auto const selected{value()};
      if(selected == "none") music_override = 0;
      else if(selected == "soundblaster-fm") music_override = 3;
      else if(selected == "roland-lapc") music_override = 2;
      else if(selected == "roland-scc1a") { music_override = 4;canvas_model = tfx::audio::sound_canvas_model::scc1a; }
      else if(selected == "roland-sc55") { music_override = 4;canvas_model = tfx::audio::sound_canvas_model::sc55; }
      else throw std::runtime_error{"music must be none, soundblaster-fm, roland-lapc, roland-scc1a or roland-sc55"};
    }
    else if(key == "--language") {
      language = value();
      language_selected = true;
      std::array<std::string_view,5> constexpr languages{"english","french","german","spanish","italian"};
      if(std::ranges::find(languages,language) == languages.end()) throw std::runtime_error{"unknown TFX language: " + language};
    }
    else if(key == "--skip-intro") skip_intro = true;
    else if(key == "--mission") {
      direct_mission = true;
      auto const selected{value()};
      mission_name = "miss" + std::to_string(number(selected));
    } else if(key == "--joystick") {
      joystick = number(value());
      if(*joystick > GLFW_JOYSTICK_LAST) throw std::runtime_error{"joystick index must be between 0 and 15"};
      control_override = tfx::flight::control_source::joystick;
    } else if(key == "--control") {
      auto const selected{value()};
      if(selected == "keyboard") control_override = tfx::flight::control_source::keyboard;
      else if(selected == "mouse") control_override = tfx::flight::control_source::mouse;
      else if(selected == "joystick") control_override = tfx::flight::control_source::joystick;
      else throw std::runtime_error{"control must be keyboard, mouse or joystick"};
    } else if(key == "--flight-model") {
      model_selected = true;
      auto const selected{value()};
      if(selected == "arcade") model = tfx::simulation::flight_model::arcade;
      else if(selected == "simple") model = tfx::simulation::flight_model::simple;
      else if(selected == "military-spec") model = tfx::simulation::flight_model::military_spec;
      else if(selected == "realistic") model = tfx::simulation::flight_model::realistic;
      else throw std::runtime_error{"flight model must be arcade, simple, military-spec or realistic"};
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
  auto preferences{tfx::configuration::load(archive_path.parent_path())};
  if(model_selected) preferences.model = model;
  if(music_override) preferences.music = *music_override;
  if(control_override) preferences.preferred_control = preferences.control = *control_override;
  if(control_override == tfx::flight::control_source::joystick && preferences.model == tfx::simulation::flight_model::arcade) throw std::runtime_error{"joystick steering requires Simple, Military-spec or Realistic flight; Arcade uses relative mouse/arrow input"};
  if(control_override == tfx::flight::control_source::mouse && preferences.model == tfx::simulation::flight_model::simple) throw std::runtime_error{"the original Simple model has no mouse steering; choose keyboard or joystick"};
  std::array<std::string_view,5> constexpr language_names{"english","french","german","spanish","italian"};
  if(!language_selected && preferences.language >= 1 && preferences.language <= language_names.size()) language = language_names[preferences.language - 1];
  tfx::resources::archive const game{archive_path};
  tfx::resources::executable_tables const tables{archive_path.parent_path() / "TFX.DAT"};
  std::unique_ptr<tfx::audio::runtime> sound;
  std::unique_ptr<tfx::platform::audio_output> output;
  if(!screenshot && !inspect) {
    std::unique_ptr<tfx::audio::music_player> music;
    if(preferences.music >= 1 && preferences.music <= 4) {
      try {
        auto const launcher{tfx::resources::read_file(archive_path.parent_path() / "START.EXE")};
        if(preferences.music == 2) music = std::make_unique<tfx::audio::music_player>(game,launcher,
          rom_directory.value_or(archive_path.parent_path()),tfx::platform::audio_output::sample_rate);
        else if(preferences.music == 4) music = std::make_unique<tfx::audio::music_player>(game,launcher,
          tfx::audio::make_scc_music_device(launcher,std::make_unique<tfx::audio::sc55_synth>(rom_directory.value_or(archive_path.parent_path()),tfx::platform::audio_output::sample_rate,canvas_model)),tfx::platform::audio_output::sample_rate);
        else music = std::make_unique<tfx::audio::music_player>(game,launcher,
          tfx::audio::make_fm_music_device(launcher,tfx::platform::audio_output::sample_rate),tfx::platform::audio_output::sample_rate);
      } catch(std::exception const &error) {
        std::cerr << "Music unavailable: " << error.what();
        if(preferences.music == 2 || preferences.music == 4) std::cerr << "; use --rom-dir to select your Roland ROM directory";
        std::cerr << ".\n";
      }
    }
    if(music) music->configure(static_cast<tfx::audio::music_mode>(preferences.music),preferences.sound_effects,tables.music_orders);
    if(preferences.sound_effects || music) {
      try {
        sound = std::make_unique<tfx::audio::runtime>(tables.samples,game,tfx::platform::audio_output::sample_rate,preferences.sound_effects != 0,std::move(music));
        output = std::make_unique<tfx::platform::audio_output>([](void *const user, std::span<float> const pcm) noexcept {
          static_cast<tfx::audio::runtime*>(user)->render(pcm);
        },sound.get());
      } catch(std::exception const &error) {
        std::cerr << "Sound output unavailable: " << error.what() << '\n';
        sound.reset();
      }
    }
  }
  if(!presentation.empty()) {
    tfx::platform::play_presentation(game,tables,presentation,presentation_function,language,scale,frame_limit,screenshot,sound.get());
    return EXIT_SUCCESS;
  }
  tfx::world::flak_state flak_state;
  tfx::world::sky_state sky_state;
  tfx::platform::flight_options const flight{
    .mission{mission_name},
    .data_directory{archive_path.parent_path()},
    .environment{override_environment},
    .grid{override_grid},
    .cell{override_cell ? std::optional<vec2<unsigned int>>{std::in_place,*override_cell} : std::nullopt},
    .screenshot{screenshot},
    .joystick{joystick},
    .scale{scale},
    .scene_radius{scene_radius},
    .frame_limit{frame_limit},
    .flight_steps{flight_steps},
    .preferences{preferences},
    .flak{flak_state},
    .sky{sky_state},
    .sound{sound.get()},
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
