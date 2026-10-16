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
#include "actors/air.h"
#include "actors/program.h"
#include "actors/surface.h"
#include "actors/surface_combat.h"
#include "actors/scenery.h"
#include "actors/contact_region.h"
#include "flight/arcade.h"
#include "flight/damage.h"
#include "flight/fuel_gauge.h"
#include "cockpit/hud.h"
#include "cockpit/radio_ticker.h"
#include "cockpit/weapon_display.h"
#include "cockpit/frame.h"
#include "cockpit/initialisation.h"
#include "cockpit/scene_display.h"
#include "missions/initialisation.h"
#include "missions/timeline.h"
#include "missions/progress.h"
#include "platform/window.h"
#include "platform/arming.h"
#include "platform/flight.h"
#include "render/camera.h"
#include "render/framebuffer.h"
#include "render/software_renderer.h"
#include "resources/archive.h"
#include "resources/executable_tables.h"
#include "simulation/timing.h"
#include "sensors/air.h"
#include "sensors/ground.h"
#include "world/assets.h"
#include "world/environment.h"
#include "world/scene.h"
#include "weapons/runtime.h"
#include "weapons/cannon.h"
#include "weapons/cannon_prediction.h"
#include "weapons/impact_prediction.h"

namespace tfx::platform {

bool fly_mission(resources::archive const &game, resources::executable_tables const &tables,
  flight_options const &options, missions::variables &campaign, window *const shared_window) {
  auto const &mission_name{options.mission};
  auto const &override_environment{options.environment};
  auto const &override_grid{options.grid};
  auto const &override_cell{options.cell};
  auto const &screenshot{options.screenshot};
  auto const scale{options.scale}, scene_radius{options.scene_radius}, frame_limit{options.frame_limit}, flight_steps{options.flight_steps};
  bool inspect{options.inspect};
  tfx::world::mission const selected{game,mission_name};
  auto const mission_setup{tfx::missions::initialise(selected.script)};
  tfx::world::environment const environment{game,override_grid.empty() ? selected.grid_name() : override_grid,override_environment.empty() ? mission_setup.environment : override_environment};
  auto const colours{tfx::render::decode_palette(game.read("colours/" + environment.palette_name + ".col"))};
  tfx::world::assets assets{game};
  tfx::world::scene scene{environment,assets};
  tfx::missions::timeline mission_time{mission_setup};
  tfx::missions::progress mission_progress{mission_setup};
  tfx::missions::finish_program const mission_finish{selected.script};
  auto const initial_campaign{campaign};
  bool const campaign_flight{shared_window != nullptr};
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
  tfx::cockpit::radio_ticker radio{tables.instruments().radio_padding};
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
  armament.fit_default(mission_setup.weapons);
  if(campaign_flight && !inspect && !mission_setup.default_weapons) {
    if(!arm_mission(*shared_window,game,tables,armament,mission_setup.aircraft,mission_setup.weapons)) return false;
  }
  auto const initial_stores{armament.pylons};
  tfx::sensors::air_contacts radar;
  tfx::sensors::air_lock seeker;
  std::vector<tfx::sensors::air_contact> radar_actors;
  tfx::sensors::designator designator;
  bool designator_view{false};
  bool navigation_mode{true};
  std::optional<tfx::weapons::target_reference> ground_designation;
  vec3<int32_t> designated_point{0,0,0};
  std::optional<tfx::sensors::mobile_designation> mobile_designation;
  std::vector<tfx::sensors::surface_contact> ground_contacts;
  int16_t radiation_cursor{0};
  tfx::sensors::designator_controls designator_input;
  bool designate_trigger{false};
  tfx::weapons::cannon_state cannon;
  tfx::flight::damage_state player_damage;
  auto const instrument_setup{tfx::cockpit::initialise_instruments(mission_setup.aircraft,mission_setup.start.landed)};
  tfx::cockpit::hud_selection display_selection{instrument_setup.displays};
  tfx::cockpit::cockpit_position cockpit_position{tables.instruments(),instrument_setup.offset};
  unsigned int ground_target_page{0};
  tfx::flight::fuel_gauge fuel_display{instrument_setup.fuel};
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
    display_selection.right = static_cast<uint16_t>(player_damage.right_display_selection);
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
    .designation_position{[&] { return vec3<int32_t>{designated_point}; }},
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
        radio.show(data.text);
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
      std::vector<tfx::actors::surface_air_target> surface_air_targets;
      for(unsigned int index{0}; index != air_simulation.aircraft().size(); ++index) if(auto const &actor{air_simulation.aircraft()[index]}) surface_air_targets.push_back({
        .actor{index},
        .position{vec3<int32_t>{actor->flight.pose.position}},
        .flags{actor->flight.pose.flags},
      });
      for(unsigned int index{0}; index != surface_actors.size(); ++index) {
        auto &actor{surface_actors[index]};
        // Requests execute inside the route callback, before this unit's movement, matching the native launcher boundary.
        tfx::actors::advance_surface(actor.state,*actor.profile,[&](tfx::actors::surface_request const &request) {
          if(request.kind == tfx::actors::surface_request_kind::radio) {
            radio.show(request.text);
          } else if(request.kind == tfx::actors::surface_request_kind::nearby_targets) {
            for(auto const &shot : tfx::actors::engage_surface_targets(actor.state,*actor.profile,{
              .owner{index},
              .player{vec3<int32_t>{air_world.player->position}},
              .aircraft{player.aircraft},
              .aircraft_targets{surface_air_targets},
            },air_simulation.random_stream())) projectiles.launch(shot);
          } else if(request.kind == tfx::actors::surface_request_kind::ground_target) {
            bool const intact{request.cell.x >= 0 && request.cell.y >= 0 && scene.terrain_intact(static_cast<unsigned int>(request.cell.x),static_cast<unsigned int>(request.cell.y))};
            if(auto const shot{tfx::actors::surface_ground_attack(actor.state,index,request,intact)}) projectiles.launch(*shot);
          }
        });
      }
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
  tfx::render::software_renderer renderer{tables}, camera_renderer{tables};
  tfx::cockpit::hud instruments{tables.instruments(),game,tables.weapons,environment.schematic_name};
  tfx::cockpit::scene_displays scene_displays{tables.instruments()};
  tfx::cockpit::frame cockpit_frame{tables.instruments(),game};
  tfx::cockpit::weapon_display aiming{tables.instruments(),game};
  auto const flight_view{[&] {
    auto view{tfx::render::aircraft_camera(player.position,player.orientation)};
    view.projection_origin = cockpit_frame.projection_origin(tfx::cockpit::forward_cockpit,cockpit_frame.clamp(tfx::cockpit::forward_cockpit,cockpit_position.value()));
    return view;
  }};
  std::vector<vec3<int32_t>> map_targets;
  for(auto const &target : mission_setup.targets) map_targets.emplace_back(target.position);
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
    if(change.clear_tracking) { seeker.tracking.reset(); seeker.guidance.reset(); ground_designation.reset(); mobile_designation.reset(); }
  }};
  auto const select_weapon{[&](tfx::weapons::weapon_role const role) {
    if(player.collision) return;
    if(armament.selected == tfx::weapons::no_pylon) armament.selected = 0;
    navigation_mode = false;
    apply_selection(armament.select(role,true));
    armament.guns = armament.selected == tfx::weapons::no_pylon || armament.selected == tfx::weapons::cannon_pylon;
  }};
  auto const selected_weapon{[&]()->tfx::weapons::definition const* {
    if(armament.guns || armament.selected < 0 || armament.selected >= tfx::weapons::cannon_pylon) return nullptr;
    auto const index{armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
    return index < tables.weapons.size() ? &tables.weapons[index] : nullptr;
  }};
  auto const refresh_ground_contacts{[&] {
    ground_contacts.clear();
    for(auto const &actor : surface_actors) ground_contacts.push_back({
      .slot{actor.state.pose.slot},
      .position{vec3<int32_t>{actor.state.pose.position}},
      .heading{actor.state.pose.angles.y},
      .side{actor.profile->side},
      .flags{static_cast<uint8_t>(actor.state.pose.flags)},
      .type{scene.actor_type(actor.visual)},
      .damage_centres{scene.actor_damage_centres(actor.visual)},
    });
  }};
  auto const surface_index{[&](unsigned int const slot) {
    auto const found{std::ranges::find_if(surface_actors,[&](auto const &actor) { return actor.state.pose.slot == slot; })};
    if(found == surface_actors.end()) throw std::runtime_error{"ground target refers to an absent surface slot"};
    return static_cast<unsigned int>(found - surface_actors.begin());
  }};
  auto const cycle_target{[&] {
    auto const *weapon{selected_weapon()};
    if(!weapon || weapon->role == tfx::weapons::weapon_role::air) { radar.next(); return; }
    if(weapon != &tables.weapons[std::to_underlying(tfx::weapons::weapon_id::harm)] && weapon != &tables.weapons[std::to_underlying(tfx::weapons::weapon_id::sidearm)]) return;
    refresh_ground_contacts();
    if(auto const slot{tfx::sensors::next_radiation_target(radiation_cursor,ground_contacts)}) {
      designated_point = vec3<int32_t>{surface_actors[surface_index(*slot)].state.pose.position};
      ground_designation.emplace(tfx::weapons::target_reference{.designated{true}});
      mobile_designation.reset();
    } else ground_designation.reset();
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
    refresh_ground_contacts();
    if(mobile_designation) designated_point = tfx::sensors::mobile_target_point(surface_actors[surface_index(mobile_designation->slot)].state.pose.position,mobile_designation->offset);
    if(designator_view) {
      if(ground_designation) tfx::sensors::follow_designation(designator,player.integer_position,ground_designation->actor ? actor_position(*ground_designation->actor) : designated_point);
      else tfx::sensors::aim_designator(designator,player.integer_position,player.angles,player.aircraft,designator_input);
      if(designate_trigger) {
        designated_point = vec3<int32_t>{vec3<uint32_t>{designator.point} * static_cast<uint32_t>(tfx::actors::position_unit)};
        auto const *weapon{selected_weapon()};
        if(weapon == &tables.weapons[std::to_underlying(tfx::weapons::weapon_id::maverick)]) {
          mobile_designation = tfx::sensors::nearest_mobile_target(designated_point,ground_contacts);
          if(mobile_designation) designated_point = tfx::sensors::mobile_target_point(surface_actors[surface_index(mobile_designation->slot)].state.pose.position,mobile_designation->offset);
        }
        ground_designation.emplace(tfx::weapons::target_reference{.designated{true}});
        designate_trigger = false;
      }
    }
    unsigned int const weapon{armament.selected < 0 ? 0u : armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
    if(weapon >= tables.weapons.size()) { seeker.clear(); return; }
    auto const view{flight_view()};
    tfx::sensors::advance_air_lock(seeker,radar,radar_actors,tables.weapons[weapon],{
      .position{vec3<int32_t>{player.integer_position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .elapsed{elapsed},
      .guns{armament.guns},
      .centre{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)},
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
    campaign = initial_campaign;
    for(auto const name : {"a2akills","a2gkills","num_miss","num_hours","miss_val","score","fmobile_down"}) campaign.try_emplace(name,0);
    player = {};
    cannon = {};
    player_damage = {};
    display_selection = instrument_setup.displays;
    player_damage.systems = instrument_setup.systems;
    ground_target_page = 0;
    fuel_display = instrument_setup.fuel;
    armament.pylons = initial_stores;
    armament.selected = 0;
    armament.select(mission_setup.aircraft == tfx::flight::player_aircraft::nighthawk ? tfx::weapons::weapon_role::ground : tfx::weapons::weapon_role::air,false);
    armament.guns = true;
    navigation_mode = true;
    radio.clear();
    radar = {};
    seeker = {};
    designator = {};
    designator_view = false;
    ground_designation.reset();
    mobile_designation.reset();
    radiation_cursor = 0;
    player.aircraft = mission_setup.aircraft;
    tfx::flight::initialise_arcade(player,mission_setup.start.position,mission_setup.angles,mission_setup.speed_factor,mission_setup.start.landed,ground);
  }};
  auto const advance_world{[&](tfx::flight::flight_controls const &controls, tfx::simulation::timer_ticks const elapsed, bool const fire = false, bool const release_store = false) {
    if(mission_progress.ended) return;
    for(auto const index : mission_time.begin_frame()) {
      radio.show(mission_setup.messages[index].text);
    }
    launch_elapsed = elapsed;
    bool const flying{!player.collision};
    auto const previous{vec3<int32_t>{player.integer_position}};
    if(release_store && !player_disabled && !armament.guns && armament.selected >= 0 && armament.selected < tfx::weapons::cannon_pylon && !player.landed) {
      auto const &weapon{tables.weapons.at(armament.pylons[static_cast<unsigned int>(armament.selected)].weapon)};
      // Native Space first acquires a ship for Harpoon; a subsequent press releases it. Laser stores require a designation.
      auto const status{player_damage.condition(tfx::flight::aircraft_system::weapons)};
      bool const trigger_available{status != tfx::flight::system_condition::failed && (status != tfx::flight::system_condition::intermittent || air_simulation.random_stream().next() <= 3000)};
      bool acquired_ship{false};
      if(trigger_available && weapon.category == 13 && !ground_designation) {
        refresh_ground_contacts();
        if(auto const slot{tfx::sensors::nearest_ship(player.integer_position,ground_contacts,tables.ship_target_types)}) ground_designation.emplace(tfx::weapons::target_reference{
          .actor{tfx::weapons::actor_identity{
            .pool{tfx::weapons::actor_pool::surface},
            .index{surface_index(*slot)},
          }},
        });
        acquired_ship = true;
      }
      if(trigger_available && !acquired_ship && (weapon.role != tfx::weapons::weapon_role::ground || ground_designation || (weapon.category != 3 && weapon.category != 13))) {
        tfx::weapons::target_reference target{.untargeted{true}};
        if(weapon.role == tfx::weapons::weapon_role::ground && ground_designation) target = *ground_designation;
        else if(seeker.guidance) target = {
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
    fuel_display.sample(player.fuel_readout);
    player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::left_engine)] = player.left_engine ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
    player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::right_engine)] = player.right_engine ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
    // Native 0x86898 fires the held Space key after its player-physics callback, before other actors update.
    // Original nonzero checks read FLP and COM slots, despite their unrelated display names.
    if(auto const shot{tfx::weapons::fire_cannon(cannon,{
      .aircraft{player.aircraft},
      .position{vec3<int32_t>{player.integer_position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .speed{player.fixed_speed},
      .trigger{fire},
      .gun_mode{armament.guns},
      .flaps_available{player_damage.condition(tfx::flight::aircraft_system::flaps) != tfx::flight::system_condition::unavailable},
      .communications_available{player_damage.condition(tfx::flight::aircraft_system::communications) != tfx::flight::system_condition::unavailable},
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
      .arcade{!campaign_flight || (campaign.contains("arcade") && campaign.at("arcade") != 0)},
    })) {
      radio.show(notice.kind == tfx::missions::notice_kind::target_destroyed ? *mission_setup.targets[notice.target].text : *mission_setup.completion->text);
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
    cockpit_position.advance(tables.instruments().viewports[tfx::cockpit::forward_cockpit].bottom);
    refresh_sensors(elapsed);
  }};
  auto const finish_world{[&](tfx::simulation::timer_ticks const elapsed) {
    if(result_evaluated) return;
    for(auto const index : mission_time.finish_frame(elapsed)) {
      auto const &event{mission_setup.scenery_events[index]};
      scene.terrain_event(event.cell.x,event.cell.y,event.entry);
    }
    if(mission_progress.finish_frame(elapsed)) radio.show(tables.timer_expired_message);
    if(mission_progress.ended) {
      campaign["score"] = std::bit_cast<int32_t>(static_cast<uint32_t>(campaign["score"]) + static_cast<uint32_t>(mission_progress.return_score));
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
  tfx::render::framebuffer flight_frame;
  auto const queue_projectiles{[&] {
    for(auto const &[_,shot] : projectiles.projectiles()) if(!shot->spent) scene.queue_actor(weapon_visuals[shot->state.weapon][shot->state.secondary],vec3d{shot->state.position} / tfx::actors::position_unit,shot->state.angles);
  }};
  auto const draw_instruments{[&] {
    std::array<std::vector<tfx::cockpit::radar_aircraft>,2> air_contacts;
    std::array<std::vector<tfx::cockpit::radar_surface>,2> surface_contacts;
    for(unsigned int pool{0}; pool != air_contacts.size(); ++pool) for(unsigned int reverse{tfx::actors::aircraft_per_side}; reverse; --reverse) {
      unsigned int const index{pool * tfx::actors::aircraft_per_side + reverse - 1};
      auto const &actor{air_simulation.aircraft()[index]};
      if(!actor || (actor->flight.pose.flags & std::to_underlying(tfx::actors::air_flag::retired))) continue;
      air_contacts[pool].push_back({
        .position_q8{vec3<int32_t>{actor->flight.pose.position}},
        .selected{radar.selected == index},
      });
    }
    for(unsigned int reverse{static_cast<unsigned int>(surface_actors.size())}; reverse; --reverse) {
      auto const &actor{surface_actors[reverse - 1]};
      auto const flags{actor.state.pose.flags};
      if(flags & std::to_underlying(tfx::actors::surface_flag::retired)) continue;
      unsigned int const pool{flags & std::to_underlying(tfx::actors::surface_flag::hostile) ? 0u : 1u};
      surface_contacts[pool].push_back({
        .position_q8{vec3<int32_t>{actor.state.pose.position}},
        .type{scene.actor_type(actor.visual)},
      });
    }
    std::vector<tfx::cockpit::radar_projectile> radar_projectiles;
    for(auto const &[_,shot] : projectiles.projectiles()) if(!shot->spent) radar_projectiles.push_back({
      .position_q8{vec3<int32_t>{shot->state.position}},
      .weapon{static_cast<tfx::weapons::weapon_id>(shot->state.weapon)},
      .player_owned{shot->owner.pool == tfx::weapons::actor_pool::player},
    });
    tfx::cockpit::hud_state state;
    auto &readings{state.instruments};
    readings.aircraft = player.aircraft;
    readings.offset = cockpit_frame.clamp(tfx::cockpit::forward_cockpit,cockpit_position.value());
    readings.systems = player_damage.systems;
    auto const switched_system{[&](tfx::flight::aircraft_system const system, bool const active) {
      auto &condition{readings.systems[std::to_underlying(system)]};
      if(condition != tfx::flight::system_condition::failed && condition != tfx::flight::system_condition::intermittent) condition = active ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
    }};
    switched_system(tfx::flight::aircraft_system::landing_gear,player.gear_down);
    switched_system(tfx::flight::aircraft_system::wheel_brakes,player.wheel_brake);
    switched_system(tfx::flight::aircraft_system::air_brake,player.air_brake);
    readings.speed = player.fixed_speed;
    readings.height = player.position.y;
    readings.heading = player.angles.y;
    readings.fuel = player.fuel;
    readings.fuel_gauge = fuel_display.reading;
    readings.smoothed_fuel_burn = fuel_display.smoothed_burn;
    readings.throttle = player.throttle;
    readings.engine_load = {static_cast<double>(player.left_engine),static_cast<double>(player.right_engine)};
    readings.inventory = &armament;
    readings.confirmed_target = seeker.guidance.has_value() || ground_designation.has_value();
    state.position = vec3<int32_t>{player.integer_position};
    state.ticks = mission_time.elapsed();
    state.clock_offset = static_cast<uint32_t>(mission_setup.clock);
    state.elapsed = launch_elapsed;
    state.chaff = instrument_setup.chaff;
    state.flares = instrument_setup.flares;
    state.stealth = instrument_setup.stealth;
    state.stall_recovery = player.recovering;
    // This host repaints the full framebuffer, so request a full refresh of cached indicators.
    state.redraw_phase = 2;
    state.afterburner_pips = player.afterburner;
    state.low_speed_ground_contact = player.low_speed_ground_contact;
    state.landed = player.landed;
    state.contacts = {
      .enemy_aircraft{air_contacts[0]},
      .allied_aircraft{air_contacts[1]},
      .enemy_surface{surface_contacts[0]},
      .allied_surface{surface_contacts[1]},
      .projectiles{radar_projectiles},
    };
    state.targets = map_targets;
    std::optional<vec3<int32_t>> range_target;
    if(ground_designation) range_target.emplace(designated_point.x >> 8,designated_point.y >> 8,designated_point.z >> 8);
    else if(radar.selected && air_simulation.aircraft()[*radar.selected]) {
      auto const &target{air_simulation.aircraft()[*radar.selected]->flight.pose.position};
      range_target.emplace(target.x >> 8,target.y >> 8,target.z >> 8);
    }
    auto const *weapon{selected_weapon()};
    auto const &range_weapon{weapon ? *weapon : tables.weapons[std::to_underlying(tfx::weapons::weapon_id::cannon)]};
    if(range_target) {
      int32_t const distance{tfx::math::distance_estimate(player.integer_position,*range_target)};
      state.in_range = distance != 0 && distance < range_weapon.range;
    }
    auto const radio_window{radio.advance(launch_elapsed)};
    if(radio_window) state.radio_message = *radio_window;
    auto const result{instruments.draw(renderer,display_selection,state,air_simulation.random_stream(),nullptr,[&](tfx::cockpit::display_side const side, tfx::cockpit::display_page const page, tfx::cockpit::mfd_state const &display) {
      tfx::cockpit::scene_camera_state camera_state{
        .aircraft{player.aircraft},
        .position{vec3<int32_t>{player.integer_position}},
        .angles{vec3<tfx::math::angle>{player.angles}},
        .free_angles{designator_view ? vec2<tfx::math::angle>{designator.pitch,designator.heading} : vec2<tfx::math::angle>{player.angles.x,player.angles.y}},
        .tracked_position_q8{},
        .tracking_roll{0},
        .ground_target{0,0,0},
      };
      if(ground_designation) camera_state.tracked_position_q8.emplace(vec3<int32_t>{designated_point});
      if(!mission_setup.targets.empty()) camera_state.ground_target = vec3<int32_t>{mission_setup.targets[ground_target_page].position};
      scene_displays.draw(renderer,side,page,display.offset,camera_state,[&](tfx::cockpit::scene_camera_request const &request) {
        auto camera{request.view()};
        camera.far_distance = scene_radius * tfx::world::cell_units;
        camera_renderer.background(camera,0,32);
        queue_projectiles();
        scene.draw(camera_renderer,camera,scene_radius);
        // The current world painter renders a whole software target; copy its viewport
        // into the instrument target. The original world raster's clipping is separate work.
        int const top{request.minimum.y + (request.maximum.y < tfx::render::screen_height ? 1 : 0)};
        int const bottom{std::min(tfx::render::screen_height - 1,request.maximum.y - 1)};
        for(int y{std::max(0,top)}; y <= bottom; ++y) for(int x{std::max(0,request.minimum.x)}; x <= std::min(tfx::render::screen_width - 1,request.maximum.x); ++x) {
          unsigned int const pixel{static_cast<unsigned int>(y * tfx::render::screen_width + x)};
          renderer.output.pixels[pixel] = camera_renderer.output.pixels[pixel];
        }
        renderer.clipping = tfx::render::raster_clip::viewport({0,0},{tfx::render::screen_width - 1,tfx::render::screen_height - 1});
        if(!request.tracked_position) return vec2<int16_t>{0,0};
        auto const point{camera.transform(vec3d{*request.tracked_position})};
        if(point.z <= 0) return vec2<int16_t>{-32000,-32000};
        auto const screen{camera.project(point)};
        return vec2<int16_t>{static_cast<int16_t>(std::clamp(screen.x,-32768.0,32767.0)),static_cast<int16_t>(std::clamp(screen.y,-32768.0,32767.0))};
      });
    })};
    player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::fuel)] = result.fuel_condition;
    // The compositor returns its warning sound event; the audio backend is still pending.
  }};
  auto const draw_aiming{[&](tfx::render::camera const &view) {
    auto const fault{player_damage.condition(tfx::flight::aircraft_system::hud)};
    if(fault == tfx::flight::system_condition::failed || (fault == tfx::flight::system_condition::intermittent && (air_simulation.random_stream().next() & 1))) return;
    auto const offset{cockpit_frame.clamp(tfx::cockpit::forward_cockpit,cockpit_position.value())};
    unsigned int const weapon_index{armament.selected < 0 ? 0u : armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
    auto const &weapon{tables.weapons.at(weapon_index < tables.weapons.size() ? weapon_index : 0)};
    auto const role{armament.selected_role()};
    tfx::cockpit::weapon_display_state state{
      .mode{navigation_mode ? tfx::cockpit::aiming_mode::navigation : role == tfx::weapons::weapon_role::ground ? tfx::cockpit::aiming_mode::ground : tfx::cockpit::aiming_mode::air},
      .aircraft{player.aircraft},
      .weapon{weapon.label},
      .range{weapon.range},
      .cannon{weapon_index == 0},
      .ammunition{cannon.ammunition},
      .air_lock{seeker.guidance.has_value()},
      .ground_lock{ground_designation.has_value()},
      .contact_visible{radar.selected.has_value()},
      .attitude{
        .angles{vec3<tfx::math::angle>{player.angles}},
        .projection_angles{static_cast<tfx::math::angle>(-player.angles.x),static_cast<tfx::math::angle>(-player.angles.z)},
        .projection_origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)},
        .offset{vec2<int16_t>{offset}},
      },
      .flight{
        .height{player.position.y},
        .speed{player.fixed_speed},
        .mach{player.unrounded_speed_mach},
        // The current Arcade pose handoff clears native DATA 0x133f4 to zero.
        .load{0},
        .throttle{player.throttle},
        .position{vec3<int32_t>{player.integer_position}},
        .air_brake{player.air_brake},
        .brake_chute{player.brake_chute},
        .offset{vec2<int16_t>{offset}},
      },
    };
    if(state.mode == tfx::cockpit::aiming_mode::navigation || state.cannon || weapon.category == tfx::weapons::bomb_impact_category) {
      vec3<int32_t> const origin{vec3<uint32_t>{player.integer_position} * static_cast<uint32_t>(tfx::actors::position_unit)};
      auto const anchor{tfx::math::place_anchor(origin,player.angles,tables.sight_mount(player.aircraft,armament.selected))};
      auto const project_prediction{[&](vec3<int32_t> const &position) {
        auto const point{view.transform(vec3d{position} / tfx::actors::position_unit)};
        if(point.z <= 0) return vec2<int16_t>{-32000,-32000};
        auto const screen{view.project(point)};
        return vec2<int16_t>{static_cast<int16_t>(std::clamp(screen.x,-32000.0,32000.0)),static_cast<int16_t>(std::clamp(screen.y,-32000.0,32000.0))};
      }};
      if(state.mode == tfx::cockpit::aiming_mode::navigation || state.cannon) {
        auto const samples{tfx::weapons::predict_cannon(tables.weapons[0],anchor,player.angles,player.fixed_speed,tables.instruments().camera_height_bounds)};
        for(unsigned int index{0}; index != samples.size(); ++index) state.cannon_path[index] = project_prediction(samples[index]);
      }
      if(state.mode != tfx::cockpit::aiming_mode::navigation && weapon.category == tfx::weapons::bomb_impact_category) state.bomb_impact.emplace(project_prediction(tfx::weapons::predict_bomb_impact(weapon,static_cast<uint8_t>(weapon_index),anchor,player.angles,player.fixed_speed,tables.instruments().camera_height_bounds)));
    }
    aiming.draw_forward(renderer,state);
  }};
  auto const draw{[&]{
    if(paused && !inspect) {
      renderer.output = flight_frame;
      renderer.text(140,80,"PAUSED",15);
      return;
    }
    auto view{inspect ? tfx::render::inspection_camera(position,heading,pitch) : flight_view()};
    if(!inspect && designator_view) {
      double constexpr radians_per_angle{2 * std::numbers::pi / 65536};
      view = tfx::render::inspection_camera(vec3d{designator.camera},designator.heading * radians_per_angle,-tfx::math::signed_word(designator.pitch) * radians_per_angle);
    }
    view.far_distance = scene_radius * tfx::world::cell_units;
    renderer.background(view,0,32);
    queue_projectiles();
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
      if(!designator_view) draw_aiming(view);
      if(!designator_view) cockpit_frame.paint(renderer.output,tfx::cockpit::forward_cockpit,cockpit_frame.clamp(tfx::cockpit::forward_cockpit,cockpit_position.value()));
      draw_instruments();
      // Target outlines retain their integration adapter pending the original cue painters.
      uint8_t constexpr hud_colour{15};
      if(designator_view) {
        renderer.line({150,100},{170,100},hud_colour);
        renderer.line({160,90},{160,110},hud_colour);
        renderer.text(100,150,ground_designation ? "DESIGNATED" : "Z TO DESIGNATE",hud_colour);
        renderer.text(100,160,std::format("ZOOM {}",designator.zoom),hud_colour);
      } else if(ground_designation) renderer.text(100,160,"GROUND TARGET",hud_colour);
      if(seeker.tracking && !designator_view) {
        vec2d const aim{seeker.reticle.x / 256.0,seeker.reticle.y / 256.0};
        renderer.line(aim + vec2d{-5,-5},aim + vec2d{5,-5},hud_colour);
        renderer.line(aim + vec2d{5,-5},aim + vec2d{5,5},hud_colour);
        renderer.line(aim + vec2d{5,5},aim + vec2d{-5,5},hud_colour);
        renderer.line(aim + vec2d{-5,5},aim + vec2d{-5,-5},hud_colour);
      }
      if(paused) renderer.text(140,80,"PAUSED",hud_colour);
      if(player_disabled) renderer.text(120,92,"AIRCRAFT LOST",hud_colour);
      else if(player_damage.accumulated != 0) renderer.text(5,50,"SYSTEM DAMAGE",hud_colour);
      flight_frame = renderer.output;
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
    return true;
  }
  std::unique_ptr<tfx::platform::window> owned_window;
  if(!shared_window) owned_window = std::make_unique<tfx::platform::window>(scale);
  auto &window{shared_window ? *shared_window : *owned_window};
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
      if(pressed(GLFW_KEY_F)) { armament.guns = true;navigation_mode = true; }
      if(pressed(GLFW_KEY_L) && !down(GLFW_KEY_LEFT_ALT) && !down(GLFW_KEY_RIGHT_ALT) && !player.collision && !player_disabled) radio.replay();
      if(pressed(GLFW_KEY_C)) cycle_target();
      if(pressed(GLFW_KEY_1)) display_selection.cycle_left(!mission_setup.targets.empty());
      if(pressed(GLFW_KEY_2)) display_selection.cycle_centre(player.aircraft);
      if(pressed(GLFW_KEY_3)) {
        auto const *weapon{selected_weapon()};
        display_selection.cycle_right(player.aircraft,weapon ? weapon->category : tables.weapons[0].category);
      }
      if(pressed(GLFW_KEY_R)) display_selection.cycle_range();
      if(pressed(GLFW_KEY_N) && !mission_setup.targets.empty() && !down(GLFW_KEY_LEFT_SHIFT) && !down(GLFW_KEY_RIGHT_SHIFT)) ground_target_page = (ground_target_page + 1) % static_cast<unsigned int>(mission_setup.targets.size());
      if(pressed(GLFW_KEY_Z)) {
        if(designator_view) designate_trigger = true;
        else if(auto const *weapon{selected_weapon()}; weapon && weapon->category == 3) {
          designator_view = true;
          designator.pitch = 0x500;
          designator.heading = player.angles.y;
          designator.zoom = 0;
        }
      }
      if(pressed(GLFW_KEY_X)) { ground_designation.reset(); mobile_designation.reset(); radar.selected.reset(); seeker.clear(); }
      if(pressed(GLFW_KEY_F1)) designator_view = false;
      if(pressed(GLFW_KEY_COMMA) && designator_view && designator.zoom) --designator.zoom;
      if(pressed(GLFW_KEY_PERIOD) && designator_view && designator.zoom < 10) ++designator.zoom;
      designator_input = {
        .up{down(GLFW_KEY_UP)},
        .down{down(GLFW_KEY_DOWN)},
        .left{down(GLFW_KEY_LEFT)},
        .right{down(GLFW_KEY_RIGHT)},
      };
      if(pressed(GLFW_KEY_SPACE)) store_trigger = true;
      if(!player.collision && !player_disabled) {
        if(pressed(GLFW_KEY_PAGE_UP)) cockpit_position.raise();
        if(pressed(GLFW_KEY_PAGE_DOWN)) cockpit_position.lower();
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
        if(!designator_view) {
          pitch_input += (down(GLFW_KEY_UP) - down(GLFW_KEY_DOWN)) * step->world_ticks * 4;
          roll_input += (down(GLFW_KEY_RIGHT) - down(GLFW_KEY_LEFT)) * step->world_ticks * 4;
        }
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
  glfwSetInputMode(host,GLFW_CURSOR,GLFW_CURSOR_NORMAL);
  return result_evaluated;
}

} // namespace tfx::platform
