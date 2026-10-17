#pragma once

#include "audio/runtime.h"
#include "cockpit/tactical_map.h"
#include "missions/rules.h"
#include "configuration/settings.h"
#include "platform/window.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "simulation/timing.h"
#include "world/flak.h"
#include "world/animation.h"
#include "sensors/air.h"
#include "world/sky.h"
#include "render/horizon.h"
#include "render/precipitation.h"

namespace tfx::platform {

struct flight_options {
  std::string mission{"miss501"};
  std::filesystem::path data_directory{};
  std::string environment{}, grid{};
  std::optional<vec2<unsigned int>> cell{};
  std::optional<std::filesystem::path> screenshot{};
  std::optional<unsigned int> joystick{};
  unsigned int scale{0}, scene_radius{6}, frame_limit{0}, flight_steps{0}, flight_frames{0};
  configuration::settings &preferences;
  world::flak_state &flak;
  world::sky_state &sky;
  world::animation_clock &scenery_clock;
  sensors::air_lock &seeker;
  vec2<int16_t> &projection_origin;
  render::horizon_phase &ground_phase;
  vec3<int32_t> &ground_reference;
  int16_t &nearby_hostile_count;
  int16_t &last_released_mount;
  bool &flight_information;
  bool &cannon_navigation;
  cockpit::tactical_map_animation &map_animation;
  render::precipitation &rain;
  math::random_state &session_random;
  audio::runtime *sound{nullptr};
  bool inspect{false};
};
enum class flight_result { finished, quit, enrol };
// FINISH resumes the authored campaign; the settings dialog can return to enrolment.
flight_result fly_mission(resources::archive const &game, resources::executable_tables const &tables,
  flight_options const &options, missions::variables &campaign, window *shared_window = nullptr);

} // namespace tfx::platform
