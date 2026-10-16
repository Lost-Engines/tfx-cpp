#include <algorithm>
#include <array>
#include <bit>
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
#include <type_traits>
#include <utility>
#include "actors/air.h"
#include "actors/program.h"
#include "actors/surface.h"
#include "actors/scenery.h"
#include "actors/contact_region.h"
#include "flight/arcade.h"
#include "flight/damage.h"
#include "missions/initialisation.h"
#include "missions/timeline.h"
#include "missions/progress.h"
#include "platform/window.h"
#include "render/camera.h"
#include "render/framebuffer.h"
#include "render/software_renderer.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "simulation/timing.h"
#include "sensors/air.h"
#include "world/assets.h"
#include "world/environment.h"
#include "world/scene.h"
#include "weapons/runtime.h"
#include "weapons/cannon.h"

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
                   "Enter selects air-to-air weapons; Backspace/O air-to-ground; F selects cannon/navigation.\n"
                   "C cycles radar targets; Space fires; P pauses; Escape exits.\n"
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
  tfx::missions::timeline mission_time{mission_setup};
  tfx::missions::progress mission_progress{mission_setup};
  tfx::missions::finish_program const mission_finish{selected.script};
  tfx::missions::variables campaign;
  bool result_evaluated{false};
  for(auto const &target : mission_setup.targets) scene.prepare_terrain_cell(static_cast<unsigned int>(target.position.x / tfx::world::cell_units),static_cast<unsigned int>(target.position.z / tfx::world::cell_units));
  for(auto const &event : mission_setup.scenery_events) scene.prepare_terrain_cell(event.cell.x,event.cell.y);
  auto const profiles{tfx::actors::profiles(game.read("waybin/craftype.cfg"))};
  tfx::actors::program const actor_program{game.read("waybin/" + mission_setup.waypoints + ".way")};
  auto const initial_actors{tfx::actors::initialise(actor_program,profiles,tables.formations)};
  auto const manoeuvres{tfx::actors::load_manoeuvres(game)};
  tfx::actors::air_runtime air_simulation{actor_program,initial_actors,profiles,tables.formations,tables.aircraft_envelopes,environment.variant_random_state(),manoeuvres};
  std::array<std::optional<tfx::world::scene_handle>,tfx::actors::aircraft_per_side * 2> air_visuals;
  struct surface_actor {
    tfx::actors::surface_state state;
    tfx::world::scene_handle visual;
    tfx::actors::profile const *profile;
  };
  std::vector<surface_actor> surface_actors;
  std::string radio_message;
  int radio_ticks{0};
  for(auto const &actor : initial_actors) {
    auto const profile{std::ranges::find(profiles,actor.profile_id,&tfx::actors::profile::id)};
    auto const visual{scene.create_actor(profile->definition,vec3d{actor.position} / tfx::actors::position_unit,actor.angles)};
    if(actor.kind == tfx::actors::record_kind::aircraft) air_visuals[tfx::actors::air_registry_index(actor)] = visual;
    else if(actor.kind == tfx::actors::record_kind::surface) surface_actors.push_back({
      .state{tfx::actors::create_surface(actor,actor_program)},
      .visual{visual},
      .profile{&*profile},
    });
  }
  std::vector<tfx::world::scene_handle> fixed_scenery;
  for(auto const &placement : tfx::actors::initialise_scenery(actor_program,profiles)) {
    auto const handle{scene.create_actor(placement.definition,vec3d{placement.position} / tfx::actors::position_unit,{0,0,0})};
    if(placement.event) scene.actor_event(handle,placement.event);
    fixed_scenery.push_back(handle);
  }
  tfx::weapons::armament armament{mission_setup.aircraft,tables.weapons,tables.arming};
  tfx::sensors::air_contacts radar;
  tfx::sensors::air_lock seeker;
  std::vector<tfx::sensors::air_contact> radar_actors;
  tfx::weapons::cannon_state cannon;
  tfx::flight::damage_state player_damage;
  auto const &player_disabled{mission_progress.player_ejected};
  tfx::flight::arcade_state player;
  player.aircraft = mission_setup.aircraft;
  tfx::actors::air_context air_world{
    .intact_ground_target{[&](vec2<int16_t> const &cell) {
      return cell.x >= 0 && cell.y >= 0 && scene.terrain_intact(static_cast<unsigned int>(cell.x),static_cast<unsigned int>(cell.y));
    }},
    .combat{true},
    .player_aircraft{mission_setup.aircraft},
  };
  std::array<std::array<tfx::world::scene_handle,2>,tfx::weapons::weapon_count> weapon_visuals;
  for(unsigned int index{0}; index != tables.weapons.size(); ++index) {
    auto const &definition{tables.weapons[index]};
    for(unsigned int appearance{0}; appearance != 2; ++appearance) {
      auto const handle{scene.create_actor(appearance ? definition.secondary : definition.fired,{0,0,0},{0,0,0})};
      weapon_visuals[index][appearance] = handle;
      scene.show_actor(handle,false);
    }
  }
  std::array<char const*,3> constexpr player_definitions{"efa","f_117a","f_22"};
  auto const player_visual{scene.create_actor(player_definitions.at(std::to_underlying(player.aircraft) - 1),{0,0,0},{0,0,0})};
  scene.show_actor(player_visual,false);
  auto const damage_player{[&](int const percentage) {
    tfx::flight::apply_damage(player_damage,percentage,air_simulation.random_stream(),false,[&] { scene.actor_event(player_visual,13); });
  }};
  std::array<std::optional<tfx::weapons::projectile_id>,tfx::actors::player_air_target> incoming;
  std::array<std::optional<tfx::actors::air_threat>,tfx::actors::player_air_target> threats;
  auto const actor_position{[&](tfx::weapons::actor_identity const identity) {
    switch(identity.pool) {
    case tfx::weapons::actor_pool::player: return vec3<int32_t>{vec3<long double>{player.position} * tfx::actors::position_unit};
    case tfx::weapons::actor_pool::aircraft: return vec3<int32_t>{air_simulation.aircraft()[identity.index]->flight.pose.position};
    case tfx::weapons::actor_pool::surface: return vec3<int32_t>{surface_actors.at(identity.index).state.pose.position};
    }
    throw std::runtime_error{"invalid projectile actor identity"};
  }};
  auto const horizontal_separation{[](vec3<int32_t> const &a, vec3<int32_t> const &b) {
    auto const delta{[](int32_t const x, int32_t const y) { return std::bit_cast<int32_t>(static_cast<uint32_t>(x) - static_cast<uint32_t>(y)); }};
    return std::max(std::abs(static_cast<int64_t>(delta(a.x,b.x))),std::abs(static_cast<int64_t>(delta(a.z,b.z))));
  }};
  auto const fatal_aircraft{[&](unsigned int const index) {
    if(radar.selected == index) { radar.selected.reset(); seeker.guidance.reset(); }
    for(auto const &request : air_simulation.fatal_damage(index)) if(auto const event{std::get_if<tfx::actors::air_scenery_event>(&request.data)}) scene.actor_event(*air_visuals[index],event->entry);
  }};
  unsigned int enemy_aircraft_lost{0}, allied_aircraft_lost{0};
  tfx::simulation::timer_ticks launch_elapsed{5};
  tfx::weapons::runtime projectiles{tables.weapons,{
    .mount_state{[&] { return tfx::weapons::launch_mount{.angles{vec3<tfx::math::angle>{player.angles}},.selected{static_cast<uint8_t>(armament.selected)}}; }},
    .launch_elapsed{[&] { return launch_elapsed; }},
    .actor_position{actor_position},
    .motion_inputs{[&](tfx::weapons::active_projectile const &shot,uint16_t const ticks) {
      bool const mounted{shot.owner.pool == tfx::weapons::actor_pool::player && (shot.state.motion == tfx::weapons::flight_stage::attached || shot.state.motion == tfx::weapons::flight_stage::attached_dispenser)};
      vec3<int32_t> const anchor{mounted ? tfx::math::place_anchor(vec3<int32_t>{vec3<uint32_t>{player.integer_position} * static_cast<uint32_t>(tfx::actors::position_unit)},player.angles,tables.store_mounts[std::to_underlying(player.aircraft) - 1].at(shot.mount)) : vec3<int32_t>{0,0,0}};
      return tfx::weapons::motion_context{
        .elapsed{ticks},
        .target{0,0,0},
        .player_owned{shot.owner.pool == tfx::weapons::actor_pool::player},
        .launch_anchor{vec3<int32_t>{anchor}},
        .player_angles{vec3<tfx::math::angle>{player.angles}},
        .player_speed{player.fixed_speed},
        .target_is_player{shot.target.actor && shot.target.actor->pool == tfx::weapons::actor_pool::player},
      };
    }},
    .reset_visual{[&](unsigned int const weapon,bool const secondary) { scene.actor_event(weapon_visuals[weapon][secondary],0); }},
    .launched{[&](tfx::weapons::active_projectile const &shot) {
      if(!shot.target.actor || shot.target.actor->pool != tfx::weapons::actor_pool::aircraft) return;
      auto const index{shot.target.actor->index};
      auto const &actor{air_simulation.aircraft()[index].value()};
      int64_t const distance{horizontal_separation(shot.state.position,actor.flight.pose.position)};
      auto const range{std::bit_cast<int32_t>(static_cast<uint32_t>(actor.combat.evasion_range) * (5280u * 32u))};
      if(distance > range) return;
      if(incoming[index]) {
        auto const found{projectiles.projectiles().find(*incoming[index])};
        if(found != projectiles.projectiles().end() && horizontal_separation(found->second->state.position,actor.flight.pose.position) < distance) return;
      }
      incoming[index] = shot.id;
      threats[index] = tfx::actors::air_threat{
        .position{vec3<int32_t>{shot.state.position}},
        .weapon{shot.state.weapon},
      };
    }},
    .target_cleared{[&](tfx::weapons::active_projectile const &shot) {
      if(shot.target.actor && shot.target.actor->pool == tfx::weapons::actor_pool::aircraft) {
        auto &current{incoming[shot.target.actor->index]};
        if(current == shot.id) { current.reset(); threats[shot.target.actor->index].reset(); }
      }
    }},
    .contacts{[&](tfx::weapons::active_projectile &shot,uint16_t const ticks) {
      auto const source{weapon_visuals[shot.state.weapon][shot.state.secondary]};
      auto const world_position{[](vec3<int32_t> const &position) { return vec3<int32_t>{position.x >> tfx::actors::position_fraction_bits,position.y >> tfx::actors::position_fraction_bits,position.z >> tfx::actors::position_fraction_bits}; }};
      auto const previous{world_position(shot.state.previous)}, current{world_position(shot.state.position)};
      auto const response{[&](uint16_t const damage) { scene.apply_actor_contact_damage(source,damage); }};
      uint16_t const damage{scene.actor_impact_damage(source)};
      using tfx::weapons::flight_stage;
      bool const released{shot.state.motion != flight_stage::attached && shot.state.motion != flight_stage::falling && shot.state.motion != flight_stage::accelerating};
      if(!scene.actor_destroyed(source) && released && shot.owner.pool != tfx::weapons::actor_pool::player) scene.collide_actor(player_visual,previous,current,damage,response,damage_player);
      if(!scene.actor_destroyed(source) && released && shot.state.weapon != std::to_underlying(tfx::weapons::weapon_id::chaff) && shot.state.weapon != std::to_underlying(tfx::weapons::weapon_id::flare)) {
        int32_t const broad_phase{std::bit_cast<int32_t>(static_cast<uint32_t>(shot.state.speed) * ticks * 20u)};
        for(unsigned int index{0}; index != air_simulation.aircraft().size(); ++index) {
          auto const &actor{air_simulation.aircraft()[index]};
          if(!actor || (shot.owner.pool == tfx::weapons::actor_pool::aircraft && shot.owner.index == index)) continue;
          auto const &pose{actor->flight.pose};
          if(pose.flags & (std::to_underlying(tfx::actors::air_flag::retired) | std::to_underlying(tfx::actors::air_flag::crashed))) continue;
          if(horizontal_separation(shot.state.position,pose.position) > broad_phase) continue;
          auto const visual{*air_visuals[index]};
          if(scene.actor_destroyed(visual)) continue;
          scene.collide_actor(visual,previous,current,damage,response);
          if(scene.actor_destroyed(visual)) {
            auto const effects{mission_progress.record_air_loss(index < tfx::actors::aircraft_per_side,scene.actor_type(visual),shot.owner.pool == tfx::weapons::actor_pool::player,true,air_simulation.random_stream())};
            if(effects.radio) { radar.selected.reset(); seeker.tracking.reset(); seeker.guidance.reset(); }
            fatal_aircraft(index);
            ++(pose.side == tfx::actors::allegiance::allied ? allied_aircraft_lost : enemy_aircraft_lost);
          }
        }
        auto constexpr surface_destroyed{std::to_underlying(tfx::actors::surface_flag::destroyed)}, surface_retired{std::to_underlying(tfx::actors::surface_flag::retired)};
        for(unsigned int index{0}; index != surface_actors.size(); ++index) {
          auto &actor{surface_actors[index]};
          if(actor.state.pose.flags & surface_retired) continue;
          scene.collide_actor(actor.visual,previous,current,damage,response);
          if(!(actor.state.pose.flags & surface_destroyed) && scene.actor_destroyed(actor.visual)) {
            mission_progress.record_surface_loss((actor.state.pose.flags & std::to_underlying(tfx::actors::surface_flag::hostile)) != 0,scene.actor_type(actor.visual));
            actor.state.actions = std::to_underlying(tfx::actors::surface_action::dead);
            actor.state.input_ticks = 0;
            actor.state.pose.flags |= surface_destroyed;
          }
        }
        for(auto const handle : fixed_scenery) scene.collide_actor(handle,previous,current,damage,response);
      }
      scene.collide_terrain(previous,current,damage,false,response);
      if(scene.actor_destroyed(source)) {
        shot.spent = true;
        scene.actor_event(source,0);
      }
    }},
  }};
  air_world.emitted = [&](tfx::actors::air_request const &request) {
    std::visit([&](auto const &data) {
      using data_type = std::remove_cvref_t<decltype(data)>;
      if constexpr(std::is_same_v<data_type,tfx::actors::air_scenery_event>) scene.actor_event(*air_visuals.at(request.actor),data.entry);
      else if constexpr(std::is_same_v<data_type,tfx::actors::air_weapon>) {
        tfx::weapons::target_reference target{
          .position{vec3<int32_t>{data.target}},
        };
        if(data.target_actor) target.actor = tfx::weapons::actor_identity{
          .pool{*data.target_actor == tfx::actors::player_air_target ? tfx::weapons::actor_pool::player : tfx::weapons::actor_pool::aircraft},
          .index{*data.target_actor == tfx::actors::player_air_target ? 0u : *data.target_actor},
        };
        projectiles.launch({
          .weapon{data.weapon},
          .position{vec3<int32_t>{data.position}},
          .angles{vec3<tfx::math::angle>{data.angles}},
          .speed{data.speed},
          .owner{
            .pool{tfx::weapons::actor_pool::aircraft},
            .index{request.actor},
          },
          .target{target},
        });
      } else if constexpr(std::is_same_v<data_type,tfx::actors::air_countermeasure>) {
        tfx::weapons::actor_identity const owner{
          .pool{tfx::weapons::actor_pool::aircraft},
          .index{request.actor},
        };
        projectiles.countermeasure(owner,actor_position(owner),data.kind == tfx::actors::air_countermeasure_kind::radar,data.strength,air_simulation.random_stream());
      } else if constexpr(std::is_same_v<data_type,tfx::actors::air_radio>) {
        radio_message = data.text;
        radio_ticks = 5 * 55;
      }
    },request.data);
  };
  auto const advance_actors{[&](unsigned int const ticks){
    // Native 0x75784 visits each actor once per elapsed tick, preserving pool order.
    for(unsigned int tick{0}; tick != std::max(1u,ticks); ++tick) {
      for(unsigned int index{0}; index != incoming.size(); ++index) {
        threats[index].reset();
        if(!incoming[index]) continue;
        auto const found{projectiles.projectiles().find(*incoming[index])};
        if(found != projectiles.projectiles().end()) threats[index] = tfx::actors::air_threat{
          .position{vec3<int32_t>{found->second->state.position}},
          .weapon{found->second->state.weapon},
        };
      }
      air_world.threats = threats;
      air_simulation.advance(air_world);
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
    for(unsigned int index{0}; index != air_simulation.aircraft().size(); ++index) {
      auto const &actor{air_simulation.aircraft()[index]};
      if(!actor) continue;
      auto const visual{*air_visuals[index]};
      auto const &pose{actor->flight.pose};
      scene.place_actor(visual,vec3d{pose.position} / tfx::actors::position_unit,pose.angles);
      scene.show_actor(visual,(pose.flags & std::to_underlying(tfx::actors::air_flag::retired)) == 0 && actor->actions != std::to_underlying(tfx::actors::air_action::retire_crashed));
    }
    for(auto const &actor : surface_actors) {
      scene.place_actor(actor.visual,vec3d{actor.state.pose.position} / tfx::actors::position_unit,actor.state.pose.angles);
      scene.show_actor(actor.visual,(actor.state.pose.flags & std::to_underlying(tfx::actors::surface_flag::retired)) == 0);
    }
  }};
  tfx::render::software_renderer renderer{tables};
  // The native ground-start fallback is zero for type 50, -20 otherwise (0x8c318).
  auto const start_x{static_cast<unsigned int>(std::clamp(mission_setup.start.position.x / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_width) - 1))};
  auto const start_z{static_cast<unsigned int>(std::clamp(mission_setup.start.position.z / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_height) - 1))};
  auto const flags{assets.object(environment.variant(start_x,start_z)).flags};
  tfx::flight::ground_contact ground{
    .present{true},
    .height{static_cast<int16_t>(mission_setup.start.landed && (!(flags & 2) || (flags & 255) >> 2 != 50) ? -20 : 0)},
  };
  auto const initial_ground{ground};
  auto const apply_selection{[&](tfx::weapons::selection_change const &change) {
    if(change.clear_contact) radar.selected.reset();
    if(change.clear_tracking) { seeker.tracking.reset(); seeker.guidance.reset(); }
  }};
  auto const select_weapon{[&](tfx::weapons::weapon_role const role) {
    if(player.collision) return;
    if(armament.selected == tfx::weapons::no_pylon) armament.selected = 0;
    apply_selection(armament.select(role,true));
    armament.guns = armament.selected == tfx::weapons::no_pylon || armament.selected == tfx::weapons::cannon_pylon;
  }};
  auto const refresh_sensors{[&](tfx::simulation::timer_ticks const elapsed) {
    radar_actors.clear();
    // The original enumerator visits the enemy pool backwards, then the allied pool backwards.
    for(unsigned int pool{0}; pool != 2; ++pool) for(unsigned int reverse{tfx::actors::aircraft_per_side}; reverse; --reverse) {
      unsigned int const index{pool * tfx::actors::aircraft_per_side + reverse - 1};
      auto const &actor{air_simulation.aircraft()[index]};
      if(!actor) continue;
      auto const &pose{actor->flight.pose};
      auto const profile{std::ranges::find(profiles,pose.profile_id,&tfx::actors::profile::id)};
      radar_actors.push_back({
        .actor{index},
        .position{vec3<int32_t>{pose.position}},
        .heading{pose.angles.y},
        .flags{pose.flags},
        .side{profile->side},
      });
    }
    radar.update(player.integer_position,radar_actors);
    unsigned int const weapon{armament.selected < 0 ? 0u : armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
    if(weapon >= tables.weapons.size()) { seeker.clear(); return; }
    auto const view{tfx::render::aircraft_camera(player.position,player.orientation)};
    tfx::sensors::advance_air_lock(seeker,radar,radar_actors,tables.weapons[weapon],{
      .position{vec3<int32_t>{player.integer_position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .elapsed{elapsed},
      .guns{armament.guns},
      .project{[&](vec3<int32_t> const &position) {
        auto const transformed{view.transform(vec3d{position})};
        if(transformed.z <= 0) return vec2<int16_t>{-32000,-32000};
        auto const screen{view.project(transformed)};
        return vec2<int16_t>{static_cast<int16_t>(std::clamp(screen.x,-32768.0,32767.0)),static_cast<int16_t>(std::clamp(screen.y,-32768.0,32767.0))};
      }},
    });
  }};
  auto const restart{[&]{
    ground = initial_ground;
    mission_time.reset();
    mission_progress.reset();
    result_evaluated = false;
    campaign.clear();
    // Direct mission entry supplies a fresh pilot's statistics until the front end provides a persistent profile.
    for(auto const name : {"a2akills","a2gkills","num_miss","num_hours","miss_val","score","fmobile_down"}) campaign.emplace(name,0);
    player = {};
    cannon = {};
    player_damage = {};
    armament.fit_default(mission_setup.weapons);
    armament.selected = 0;
    armament.select(mission_setup.aircraft == tfx::flight::player_aircraft::nighthawk ? tfx::weapons::weapon_role::ground : tfx::weapons::weapon_role::air,false);
    armament.guns = true;
    radar = {};
    seeker = {};
    player.aircraft = mission_setup.aircraft;
    tfx::flight::initialise_arcade(player,mission_setup.start.position,mission_setup.angles,mission_setup.speed_factor,mission_setup.start.landed,ground);
  }};
  auto const advance_world{[&](tfx::flight::flight_controls const &controls, tfx::simulation::timer_ticks const elapsed, bool const fire = false, bool const release_store = false) {
    if(mission_progress.ended) return;
    for(auto const index : mission_time.begin_frame()) {
      radio_message = mission_setup.messages[index].text;
      radio_ticks = 5 * 55;
    }
    launch_elapsed = elapsed;
    bool const flying{!player.collision};
    auto const previous{vec3<int32_t>{player.integer_position}};
    if(release_store && !player_disabled && !armament.guns && armament.selected >= 0 && armament.selected < tfx::weapons::cannon_pylon && !player.landed) {
      auto const &weapon{tables.weapons.at(armament.pylons[static_cast<unsigned int>(armament.selected)].weapon)};
      // The Space callback requires a designation for laser/anti-ship weapons; radar missiles may be released without a lock.
      auto const status{player_damage.condition(tfx::flight::aircraft_system::weapons)};
      bool const trigger_available{status != tfx::flight::system_condition::failed && (status != tfx::flight::system_condition::intermittent || air_simulation.random_stream().next() <= 3000)};
      if(trigger_available && (weapon.role != tfx::weapons::weapon_role::ground || (weapon.category != 3 && weapon.category != 13))) {
        tfx::weapons::target_reference target{.untargeted{true}};
        if(seeker.guidance) target = {
          .actor{tfx::weapons::actor_identity{
            .pool{tfx::weapons::actor_pool::aircraft},
            .index{*seeker.guidance},
          }},
        };
        tfx::weapons::selection_change change;
        armament.fire({
          .position{vec3<int32_t>{player.integer_position}},
          .angles{vec3<tfx::math::angle>{player.angles}},
          .speed{player.fixed_speed},
          .target{target},
          .inhibited{player.collision != 0},
        },tables.store_mounts[std::to_underlying(player.aircraft) - 1],change,[&](auto const &shot) { projectiles.launch(shot); });
        apply_selection(change);
      }
    }
    if(player_disabled) tfx::flight::advance_disabled(player,controls,elapsed,ground);
    else if(flying) tfx::flight::advance_arcade(player,controls,elapsed,ground);
    player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::left_engine)] = player.left_engine ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
    player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::right_engine)] = player.right_engine ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
    // Native 0x86898 fires the held Space key after its player-physics callback, before other actors update.
    if(auto const shot{tfx::weapons::fire_cannon(cannon,{
      .aircraft{player.aircraft},
      .position{vec3<int32_t>{player.integer_position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .speed{player.fixed_speed},
      .trigger{fire},
      .gun_mode{armament.guns},
      .fire_control{player_damage.condition(tfx::flight::aircraft_system::fire_control) != tfx::flight::system_condition::unavailable},
      .gun{player_damage.condition(tfx::flight::aircraft_system::gun) != tfx::flight::system_condition::unavailable},
      .crashed{player.collision != 0},
      .ejected{player_disabled},
      .landed{player.landed},
    },tables.cannon_mounts,air_simulation.random_stream())}) projectiles.launch(*shot);
    std::vector<tfx::missions::target_life> targets;
    for(auto const &target : mission_setup.targets) targets.push_back(scene.terrain_intact(static_cast<unsigned int>(target.position.x / tfx::world::cell_units),static_cast<unsigned int>(target.position.z / tfx::world::cell_units)) ? tfx::missions::target_life::alive : tfx::missions::target_life::dead);
    for(auto const &notice : mission_progress.begin_frame({
      .mission_time{mission_time.elapsed()},
      .elapsed{elapsed},
      .targets{targets},
      .landed{player.landed},
      .speed{player.fixed_speed},
      .arcade{true},
    })) {
      radio_message = notice.kind == tfx::missions::notice_kind::target_destroyed ? *mission_setup.targets[notice.target].text : *mission_setup.completion->text;
      radio_ticks = 5 * 55;
    }
    air_world.player = tfx::actors::air_contact{
      .position{vec3<int32_t>{vec3<long double>{player.position} * tfx::actors::position_unit}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .speed{std::bit_cast<int32_t>(static_cast<uint32_t>(player.fixed_speed) << tfx::actors::speed_fraction_bits)},
    };
    scene.place_actor(player_visual,vec3d{player.position},player.angles);
    tfx::flight::repair_systems(player_damage,elapsed);
    advance_actors(elapsed);
    if(flying) {
      // Native 0x72018 updates actors before collecting contacts; the next flight frame consumes this surface result.
      auto const response{[&](uint16_t const cost) { scene.apply_actor_contact_damage(player_visual,cost); damage_player(100); }};
      ground.present = false;
      auto const collect{[&](tfx::world::instance_result const &contact) {
        if(contact.surface_present) { ground.present = true; ground.height = contact.surface_height; }
        if(contact.collisions && player.crashing) player.collision = 1;
      }};
      for(auto const handle : fixed_scenery) collect(scene.collide_actor(handle,previous,player.integer_position,0,response,damage_player,true));
      collect(scene.collide_terrain(previous,player.integer_position,0,true,response));
      // Native 0x7c724 queries nearby mobile assemblies after the terrain, including carrier decks.
      auto const region{tfx::actors::nearby_surface_region(previous,player.integer_position)};
      for(auto const &actor : surface_actors) if(!(actor.state.pose.flags & std::to_underlying(tfx::actors::surface_flag::retired)) && region.contains(actor.state.pose.position)) collect(scene.collide_actor(actor.visual,previous,player.integer_position,0,response,damage_player,true));
    }
    if(mission_progress.observe_player_loss(scene.actor_destroyed(player_visual),player.collision != 0,elapsed)) scene.actor_event(player_visual,21);
    projectiles.advance(elapsed,air_simulation.random_stream());
    scene.advance(elapsed);
    refresh_sensors(elapsed);
  }};
  auto const finish_world{[&](tfx::simulation::timer_ticks const elapsed) {
    if(result_evaluated) return;
    for(auto const index : mission_time.finish_frame(elapsed)) {
      auto const &event{mission_setup.scenery_events[index]};
      scene.terrain_event(event.cell.x,event.cell.y,event.entry);
    }
    if(mission_progress.finish_frame(elapsed)) { radio_message = tables.timer_expired_message; radio_ticks = 5 * 55; }
    if(mission_progress.ended) {
      campaign["score"] = mission_progress.return_score;
      campaign["outcome"] = std::to_underlying(mission_progress.outcome);
      campaign["status"] = std::to_underlying(mission_progress.status);
      mission_finish.execute(mission_progress.results,campaign);
      result_evaluated = true;
      std::cout << "Mission result: " << campaign["miss_val"] << "; score " << campaign["score"] << "; outcome " << campaign["outcome"] << std::endl;
    }
  }};
  if(!inspect || flight_steps) restart();
  for(unsigned int step{0}; step != flight_steps; ++step) {
    advance_world({},4);
    finish_world(4);
  }
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
    for(auto const &[_,shot] : projectiles.projectiles()) if(!shot->spent) scene.queue_actor(weapon_visuals[shot->state.weapon][shot->state.secondary],vec3d{shot->state.position} / tfx::actors::position_unit,shot->state.angles);
    scene.draw(renderer,view,scene_radius);
    if(!inspect && result_evaluated) {
      // Diagnostic result display until the original presentation/menu graph supplies its result page.
      renderer.output.pixels.fill(0);
      renderer.text(90,35,"MISSION RESULTS",15);
      renderer.text(25,60,mission_progress.outcome == tfx::missions::session_outcome::aircraft_lost ? "AIRCRAFT LOST" : mission_progress.results.completed ? "OBJECTIVE COMPLETE" : "OBJECTIVE NOT COMPLETE",15);
      renderer.text(25,80,std::format("AIR KILLS {}",mission_progress.results.credited_air_kills),15);
      renderer.text(25,95,std::format("GROUND KILLS {}  TARGETS {}",mission_progress.results.credited_ground_kills,mission_progress.results.credited_targets),15);
      renderer.text(25,115,std::format("SCORE {}  RESULT {}",campaign["score"],campaign["miss_val"]),15);
      renderer.text(40,160,"ENTER OR ESCAPE TO CLOSE",15);
    } else if(!inspect) {
      // Readouts use the original miniature font; full native HUD layout/MFDs are still being connected.
      uint8_t constexpr hud_colour{15};
      renderer.text(5,5,std::format("MACH {:.2f}  ALT {} FT",player.speed_mach,static_cast<int>(-player.position.y * tfx::flight::feet_per_world_unit)),hud_colour);
      renderer.text(5,14,std::format("THR {}  FUEL {}  AB {}",static_cast<int>(player.throttle * 100),static_cast<int>(player.fuel),player.afterburner),hud_colour);
      renderer.text(5,185,std::string{player.gear_down ? "GEAR DOWN  " : "GEAR UP  "} + (player.left_engine ? "L ON  " : "L OFF  ") + (player.right_engine ? "R ON" : "R OFF"),hud_colour);
      renderer.text(245,5,"ARCADE",hud_colour);
      renderer.text(5,23,std::format("HOSTILE LOSSES {}  SHOTS {}",enemy_aircraft_lost,projectiles.projectiles().size()),hud_colour);
      if(player.aircraft != tfx::flight::player_aircraft::nighthawk) renderer.text(5,32,std::format("GUN {}",cannon.ammunition),hud_colour);
      if(!armament.guns && armament.selected >= 0) {
        auto const weapon{armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
        auto const count{std::ranges::count_if(armament.pylons,[&](auto const &slot) { return slot.weapon == weapon && slot.count; })};
        renderer.text(5,41,std::format("{} X{}",tables.weapons[weapon].label,count),hud_colour);
      }
      if(seeker.tracking) {
        vec2d const aim{seeker.reticle.x / 256.0,seeker.reticle.y / 256.0};
        renderer.line(aim + vec2d{-5,-5},aim + vec2d{5,-5},hud_colour);
        renderer.line(aim + vec2d{5,-5},aim + vec2d{5,5},hud_colour);
        renderer.line(aim + vec2d{5,5},aim + vec2d{-5,5},hud_colour);
        renderer.line(aim + vec2d{-5,5},aim + vec2d{-5,-5},hud_colour);
        renderer.text(140,160,seeker.guidance ? "LOCK" : "ACQUIRING",hud_colour);
      }
      if(paused) renderer.text(140,80,"PAUSED",hud_colour);
      if(player_disabled) renderer.text(120,92,"AIRCRAFT LOST",hud_colour);
      else if(player_damage.accumulated != 0) renderer.text(5,50,"SYSTEM DAMAGE",hud_colour);
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
  bool captured{false}, mouse_started{false}, store_trigger{false};
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
      store_trigger = false;
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
    if(result_evaluated && (pressed(GLFW_KEY_ENTER) || pressed(GLFW_KEY_KP_ENTER))) break;
    if(!inspect && !result_evaluated && pressed(GLFW_KEY_P)) paused = !paused;
    bool const capture{inspect ? glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS : !paused && !result_evaluated};
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
    std::optional<tfx::simulation::timer_ticks> frame_ticks;
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
    } else if(!paused && !result_evaluated) {
      if(pressed(GLFW_KEY_ENTER) || pressed(GLFW_KEY_KP_ENTER)) select_weapon(tfx::weapons::weapon_role::air);
      if(pressed(GLFW_KEY_BACKSPACE) || pressed(GLFW_KEY_O)) select_weapon(tfx::weapons::weapon_role::ground);
      if(pressed(GLFW_KEY_F)) armament.guns = true;
      if(pressed(GLFW_KEY_C)) radar.next();
      if(pressed(GLFW_KEY_SPACE)) store_trigger = true;
      if(!player.collision && !player_disabled) {
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
        advance_world(controls,step->world_ticks,down(GLFW_KEY_SPACE),store_trigger);
        store_trigger = false;
        frame_ticks = step->world_ticks;
        flight_clock.begin({});
      } else {
        glfwWaitEventsTimeout(.002);
        continue;
      }
    }
    if(paused || result_evaluated) glfwWaitEventsTimeout(.01);
    draw();
    window.present(renderer.output.colourise(colours));
    if(frame_ticks) finish_world(*frame_ticks);
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
