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
#include <ranges>
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
#include "flight/aerodynamic_launch.h"
#include "flight/aerodynamic_step.h"
#include "flight/aerodynamic_pilot_keys.h"
#include "flight/automatic_landing.h"
#include "flight/player_dispatch.h"
#include "flight/player_frame.h"
#include "flight/player_shared.h"
#include "flight/player_flight.h"
#include "flight/joystick.h"
#include "flight/mouse_input.h"
#include "flight/damage.h"
#include "flight/defence.h"
#include "missions/engagement.h"
#include "world/impact.h"
#include "flight/ejection_sequence.h"
#include "flight/simple.h"
#include "flight/fuel_gauge.h"
#include "cockpit/hud.h"
#include "cockpit/radio_ticker.h"
#include "cockpit/weapon_display.h"
#include "cockpit/external_display.h"
#include "cockpit/frame.h"
#include "cockpit/view_camera.h"
#include "cockpit/initialisation.h"
#include "cockpit/scene_display.h"
#include "missions/initialisation.h"
#include "missions/timeline.h"
#include "missions/progress.h"
#include "missions/recovery.h"
#include "platform/window.h"
#include "platform/arming.h"
#include "platform/flight.h"
#include "platform/configuration.h"
#include "render/camera.h"
#include "render/point_projection.h"
#include "render/palette_selection.h"
#include "render/palette_lighting.h"
#include "render/g_effects.h"
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

flight_result fly_mission(resources::archive const &game, resources::executable_tables const &tables,
  flight_options const &options, missions::variables &campaign, window *const shared_window) {
  auto &preferences{options.preferences};
  auto *const sound{options.sound};
  auto const sample{[&](audio::sample_priority const priority, auto const id) { if(sound) sound->sample(priority,id); }};
  auto const reheat_sound{[&](flight::afterburner_change const change) {
    if(change != flight::afterburner_change::none) sample(audio::sample_priority::normal,
      change == flight::afterburner_change::started || change == flight::afterburner_change::increased ? audio::sample_id::afterburner : audio::sample_id::afterburner_stop);
  }};
  bool simple_mode{preferences.model == simulation::flight_model::simple};
  bool arcade_mode{preferences.model == simulation::flight_model::arcade};
  auto const &mission_name{options.mission};
  auto const &override_environment{options.environment};
  auto const &override_grid{options.grid};
  auto const &override_cell{options.cell};
  auto const &screenshot{options.screenshot};
  auto const scale{options.scale}, scene_radius{options.scene_radius}, frame_limit{options.frame_limit}, flight_steps{options.flight_steps};
  bool inspect{options.inspect};
  tfx::world::mission const selected{game,mission_name};
  auto const mission_setup{tfx::missions::initialise(selected.script)};
  tfx::world::environment environment{game,override_grid.empty() ? selected.grid_name() : override_grid,override_environment.empty() ? mission_setup.environment : override_environment};
  environment.lighting.status = tfx::world::apply_detail_status(environment.lighting.status,preferences.detail);
  std::array<tfx::render::dac_palette,tfx::render::altitude_palette_count> altitude_palettes;
  for(unsigned int bank{0}; bank != altitude_palettes.size(); ++bank) {
    auto const bytes{game.read("colours/" + (bank ? environment.lighting.upper_palette_names[bank - 1] : environment.lighting.palette_name) + ".col")};
    if(bytes.size() != altitude_palettes[bank].size()) throw std::runtime_error{"invalid environment altitude palette"};
    std::ranges::copy(bytes,altitude_palettes[bank].begin());
  }
  tfx::render::palette_lighting palette_lighting{altitude_palettes,environment.lighting.palette_altitudes,tables.fixed_flight_palette};
  tfx::render::g_effects_state g_effects;
  auto colours{tfx::render::expand_dac_palette(palette_lighting.colours())};
  auto const infrared_colours{tfx::render::decode_palette(game.read("colours/" + environment.lighting.infrared_palette_name + ".col"))};
  auto const *frame_colours{&colours};
  tfx::render::palette_selection palette_selection;
  bool night_vision{false};
  int16_t hud_green{tfx::math::signed_word(preferences.hud_green)};
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
    if(!arm_mission(*shared_window,game,tables,armament,mission_setup.aircraft,mission_setup.weapons)) return flight_result::quit;
  }
  auto const initial_stores{armament.pylons};
  tfx::sensors::air_contacts radar;
  tfx::sensors::air_lock seeker;
  std::vector<tfx::sensors::air_contact> radar_actors;
  tfx::sensors::designator designator;
  bool designator_view{false};
  tfx::cockpit::aiming_mode aiming_mode{tfx::cockpit::aiming_mode::navigation};
  tfx::flight::refuelling refuelling{tables.refuel_parameters()};
  tfx::flight::landing_system landing;
  tfx::flight::player_flight player_flight;
  auto &ejection{player_flight.ejection};
  tfx::missions::recovery_maps const recovery{game};
  auto const ejected{[&] { return ejection.value().stage != tfx::flight::ejection_stage::cockpit; }};
  std::optional<tfx::weapons::projectile_id> camera_missile;
  std::optional<unsigned int> impact_aircraft;
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
  tfx::flight::defensive_systems const initial_defences{
    .chaff{instrument_setup.chaff},
    .flares{instrument_setup.flares},
    .stealth{instrument_setup.stealth},
  };
  auto defences{initial_defences};
  tfx::cockpit::hud_selection display_selection{instrument_setup.displays};
  tfx::cockpit::cockpit_position cockpit_position{tables.instruments(),instrument_setup.offset};
  tfx::cockpit::view_control views;
  tfx::cockpit::view_camera view_motion;
  uint16_t view_pan{0};
  unsigned int ground_target_page{0};
  auto &fuel_display{player_flight.fuel};
  fuel_display = instrument_setup.fuel;
  auto const &player_disabled{mission_progress.player_ejected};
  auto &simple_player{player_flight.basic};
  auto &physical_player{player_flight.physical};
  auto &automatic_landing{player_flight.automatic};
  auto &stick_pressure{player_flight.stick_pressure};
  auto &simple_body{player_flight.simple_body};
  simple_body = simple_mode;
  auto const &wind_parameters{tables.aerodynamic_wind[tfx::flight::aerodynamic_initial_weather]};
  auto const surface_celsius{[&]() -> std::optional<int16_t> {
    if(!preferences.effects.temperature) return {};
    return tables.aerodynamic_temperatures[tfx::flight::aerodynamic_initial_weather][tfx::flight::aerodynamic_initial_temperature_column];
  }};
  std::vector<vec2<uint8_t>> player_route;
  for(auto const &point : actor_program.player_route) player_route.emplace_back(static_cast<uint8_t>(point.x / tfx::world::cell_units),static_cast<uint8_t>(point.z / tfx::world::cell_units));
  auto &player{simple_player.flight};
  tfx::flight::simple_inputs simple_controls;
  tfx::flight::mouse_flight_input mouse_control;
  simple_controls.source = preferences.control;
  auto const body_basis{[&]() -> tfx::math::attitude const& { return player_flight.body(); }};
  player.aircraft = mission_setup.aircraft;
  tfx::actors::air_context air_world{
    .model{preferences.model},
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
  auto const aircraft_visual{scene.create_actor(player_definitions.at(std::to_underlying(player.aircraft) - 1),{0,0,0},{0,0,0})};
  auto const pilot_visual{scene.create_actor("man",{0,0,0},{0,0,0})};
  struct crash_models {
    tfx::world::scene_handle land;
    tfx::world::scene_handle water;
    tfx::world::scene_handle contact;
  };
  crash_models const crashes{
    .land{scene.create_actor("crash",{0,0,0},{0,0,0})},
    .water{scene.create_actor("plop",{0,0,0},{0,0,0})},
    .contact{scene.create_actor("kapow",{0,0,0},{0,0,0})},
  };
  for(auto const handle : {crashes.land,crashes.water,crashes.contact}) scene.show_actor(handle,false);
  std::optional<tfx::render::point_projection> impact_projection;
  auto player_visual{aircraft_visual};
  scene.show_actor(aircraft_visual,false);
  scene.show_actor(pilot_visual,false);
  tfx::simulation::timer_ticks launch_elapsed{5};
  auto const refuel_events{[&](std::span<tfx::flight::refuel_event const> const events) {
    for(auto const &event : events) {
      if(event.kind == tfx::flight::refuel_event_kind::player_model) scene.actor_event(player_visual,event.argument);
      else if(event.kind == tfx::flight::refuel_event_kind::tanker_model) scene.actor_event(*air_visuals.at(tfx::actors::aircraft_per_side + *event.tanker),event.argument);
      else if(event.kind == tfx::flight::refuel_event_kind::urgent_sample) sample(audio::sample_priority::urgent,event.argument);
      else if(event.kind == tfx::flight::refuel_event_kind::normal_sample) sample(audio::sample_priority::normal,event.argument);
      else if(event.kind == tfx::flight::refuel_event_kind::connected_voice && sound) sound->sequence(audio::sample_priority::normal,{std::to_underlying(audio::sample_id::fill_up),std::to_underlying(audio::sample_id::refuel_response)});
    }
  }};
  auto const update_refuelling{[&] {
    tfx::flight::refuel_registry allies;
    if(refuelling.value().enabled) for(unsigned int slot{0}; slot != allies.size(); ++slot) {
      unsigned int const index{tfx::actors::aircraft_per_side + slot};
      auto const &actor{air_simulation.aircraft()[index]};
      if(!actor) continue;
      auto const &pose{actor->flight.pose};
      allies[slot].emplace(tfx::flight::refuel_aircraft{
        .position_q8{vec3<int32_t>{pose.position}},
        .angles{vec3<tfx::math::angle>{pose.angles}},
        .flags{pose.flags},
        .shape_type{scene.actor_type(*air_visuals[index])},
      });
    }
    tfx::flight::refuel_player contact{
      .aircraft{player.aircraft},
      .position{vec3<int32_t>{player.integer_position}},
      .position_q8{vec3<int32_t>{vec3<long double>{player.position} * tfx::actors::position_unit}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .speed{player.fixed_speed},
    };
    auto const result{refuelling.advance(contact,allies,launch_elapsed)};
    player.integer_position = vec3<int32_t>{contact.position};
    if(result.target_override) radar.selected = tfx::actors::aircraft_per_side + *result.target_override;
    refuel_events(result.events);
    if(result.moved_tanker) {
      unsigned int const index{tfx::actors::aircraft_per_side + *result.moved_tanker};
      auto const &tanker{*allies[*result.moved_tanker]};
      air_simulation.apply_refuelling_pose(index,tanker.position_q8,tanker.angles);
      scene.place_actor(*air_visuals[index],vec3d{tanker.position_q8} / tfx::actors::position_unit,tanker.angles);
    }
  }};
  auto const damage_player{[&](int const percentage) {
    if(ejected()) return;
    tfx::flight::apply_damage(player_damage,percentage,air_simulation.random_stream(),false,[&] { scene.actor_event(player_visual,13); });
    display_selection.right = static_cast<uint16_t>(player_damage.right_display_selection);
  }};
  tfx::missions::engagement_state engagement;
  tfx::weapons::active_projectile const *launch_warning{nullptr};
  auto const permission_context{[&] {
    return tfx::missions::engagement_context{
      .aircraft{player.aircraft},
      // Direct diagnostic launches retain their existing Arcade rules exemption; campaign mode comes from the parser.
      .arcade{!campaign_flight || (campaign.contains("arcade") && campaign.at("arcade") != 0)},
      .training{campaign.contains("training") && campaign.at("training") != 0},
      .inhibited{ejected()},
    };
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
  auto const fatal_aircraft{[&](unsigned int const index, tfx::actors::air_loss_cause const cause = tfx::actors::air_loss_cause::combat) {
    if(!impact_aircraft) impact_aircraft = index;
    if(radar.selected == index) { radar.selected.reset(); seeker.guidance.reset(); }
    for(auto const &request : air_simulation.fatal_damage(index,cause)) if(auto const event{std::get_if<tfx::actors::air_scenery_event>(&request.data)}) scene.actor_event(*air_visuals[index],event->entry);
  }};
  auto const projectile_world_position{[](vec3<int32_t> const &position) {
    return vec3<int32_t>{position.x >> tfx::actors::position_fraction_bits,position.y >> tfx::actors::position_fraction_bits,position.z >> tfx::actors::position_fraction_bits};
  }};
  unsigned int enemy_aircraft_lost{0}, allied_aircraft_lost{0};
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
        .player_ejected{ejected()},
        .player_decoys{defences.ecm},
        .player_distance{tfx::math::distance_estimate(player.integer_position,projectile_world_position(shot.state.position))},
      };
    }},
    .player_distance{[&](tfx::weapons::active_projectile const &shot) {
      return tfx::math::distance_estimate(player.integer_position,projectile_world_position(shot.state.position));
    }},
    .warning{[&](tfx::weapons::projectile_warning const &warning) {
      if(sound) {
        if(warning.music) sound->music_cue(audio::music_cue_id::incoming_projectile);
        sound->sample(audio::sample_priority::urgent,warning.sample);
      }
    }},
    .reset_visual{[&](unsigned int const weapon,bool const secondary) { scene.actor_event(weapon_visuals[weapon][secondary],0); }},
    .launched{[&](tfx::weapons::active_projectile const &shot) {
      if(shot.owner.pool == tfx::weapons::actor_pool::player &&
         shot.state.weapon != std::to_underlying(tfx::weapons::weapon_id::cannon) &&
         shot.state.weapon != std::to_underlying(tfx::weapons::weapon_id::chaff) &&
         shot.state.weapon != std::to_underlying(tfx::weapons::weapon_id::flare)) camera_missile = shot.id;
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
      auto const previous{projectile_world_position(shot.state.previous)}, current{projectile_world_position(shot.state.position)};
      auto const response{[&](uint16_t const damage) { scene.apply_actor_contact_damage(source,damage); }};
      uint16_t const damage{scene.actor_impact_damage(source)};
      using tfx::weapons::flight_stage;
      bool const released{shot.state.motion != flight_stage::attached && shot.state.motion != flight_stage::falling && shot.state.motion != flight_stage::accelerating};
      if(!ejected() && !scene.actor_destroyed(source) && released && shot.owner.pool != tfx::weapons::actor_pool::player) scene.collide_actor(player_visual,previous,current,damage,response,damage_player);
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
            auto const effects{mission_progress.record_air_loss(index < tfx::actors::aircraft_per_side,scene.actor_type(visual),shot.owner.pool == tfx::weapons::actor_pool::player,engagement.authorised(permission_context()),air_simulation.random_stream())};
            if(effects.acknowledgement_sample) {
              if(sound) {
                sound->music_cue(audio::music_cue_id::player_aircraft_kill);
                sound->sequence(audio::sample_priority::normal,{std::to_underlying(audio::sample_id::aircraft_explosion),*effects.acknowledgement_sample});
              }
              radar.selected.reset(); seeker.tracking.reset(); seeker.guidance.reset();
            }
            if(effects.orders_violated) radio.show(tables.orders_violation_message,true);
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
      if(!scene.actor_destroyed(source)) {
        bool const terrain_destroyed{scene.terrain_destroyed(current)};
        scene.collide_terrain(previous,current,damage,false,response);
        if(!terrain_destroyed && scene.terrain_destroyed(current)) {
          auto const rules{permission_context()};
          auto const effects{mission_progress.record_terrain_loss({
            .cell{current.x >> tfx::world::cell_shift,current.z >> tfx::world::cell_shift},
            .player_owned{shot.owner.pool == tfx::weapons::actor_pool::player},
            .weapon{shot.state.weapon},
            .arcade{rules.arcade},
            .training{rules.training},
          })};
          if(effects.unauthorised && sound) sound->music_cue(audio::music_cue_id::unauthorised_target);
          if(effects.explosion) {
            if(effects.unauthorised && sound) sound->sequence(audio::sample_priority::normal,{std::to_underlying(audio::sample_id::aircraft_explosion),std::to_underlying(audio::sample_id::unauthorised_target)});
            else sample(audio::sample_priority::normal,audio::sample_id::aircraft_explosion);
          }
          if(effects.notice == tfx::missions::terrain_loss_notice::training_warning) radio.show(tables.ground_training_warning);
          else if(effects.notice == tfx::missions::terrain_loss_notice::violation) radio.show(tables.ground_orders_violation,true);
        }
      }
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
      } else if constexpr(std::is_same_v<data_type,tfx::actors::air_warning>) {
        auto const kind{data.kind == tfx::actors::air_warning_kind::tracking ? tfx::missions::engagement_warning::tracking : tfx::missions::engagement_warning::firing};
        for(auto const &event : engagement.observe(kind,data.target == tfx::actors::player_air_target,permission_context())) {
          if(auto const request{std::get_if<tfx::missions::engagement_sample>(&event)}) sample(request->urgent ? audio::sample_priority::urgent : audio::sample_priority::normal,request->sample);
          else radio.show(tables.fire_permission_message);
        }
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
      if(impact_aircraft == index && ((pose.flags & std::to_underlying(tfx::actors::air_flag::retired)) || actor->actions == std::to_underlying(tfx::actors::air_action::retire_crashed))) impact_aircraft.reset();
      scene.place_actor(visual,vec3d{pose.position} / tfx::actors::position_unit,pose.angles);
      scene.show_actor(visual,(pose.flags & std::to_underlying(tfx::actors::air_flag::retired)) == 0 && actor->actions != std::to_underlying(tfx::actors::air_action::retire_crashed));
    }
    for(auto const &actor : surface_actors) {
      scene.place_actor(actor.visual,vec3d{actor.state.pose.position} / tfx::actors::position_unit,actor.state.pose.angles);
      scene.show_actor(actor.visual,(actor.state.pose.flags & std::to_underlying(tfx::actors::surface_flag::retired)) == 0);
    }
  }};
  tfx::render::software_renderer renderer{tables}, camera_renderer{tables};
  tfx::cockpit::hud instruments{tables.instruments(),game,tables.weapons,environment.lighting.schematic_name};
  tfx::cockpit::scene_displays scene_displays{tables.instruments()};
  tfx::cockpit::frame cockpit_frame{tables.instruments(),game};
  tfx::cockpit::weapon_display aiming{tables.instruments(),game};
  tfx::cockpit::external_display const external_instruments{tables.instruments(),tables.presentation_fonts()};
  // The native ground-start fallback is zero for type 50, -20 otherwise (0x8c318).
  auto const start_x{static_cast<unsigned int>(std::clamp(mission_setup.start.position.x / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_width) - 1))};
  auto const start_z{static_cast<unsigned int>(std::clamp(mission_setup.start.position.z / tfx::world::cell_units,0,static_cast<int>(tfx::world::map_height) - 1))};
  auto const flags{assets.object(environment.variant(start_x,start_z)).flags};
  tfx::flight::ground_contact ground{
    .present{true},
    .height{static_cast<int16_t>(mission_setup.start.landed && (!(flags & 2) || (flags & 255) >> 2 != 50) ? -20 : 0)},
  };
  auto const initial_ground{ground};
  int16_t ground_zone{-1};
  auto const view_index{[&] { return static_cast<unsigned int>(std::to_underlying(views.value().current)); }};
  auto const camera_context{[&] {
    tfx::cockpit::view_camera_context context{
      .position{vec3<int32_t>{player.integer_position}},
      .position_q8{vec3<int32_t>{vec3<long double>{player.position} * tfx::actors::position_unit}},
      .position_f32{vec3f{player.position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .basis{player.orientation},
      .body_basis{&body_basis()},
      .elapsed{launch_elapsed},
      .pan{view_pan},
      .ground_height{ground.present ? ground.height : int16_t{0}},
      .refuel_phase{refuelling.value().phase},
      .speed{player.fixed_speed},
      .height_bounds{vec2<int32_t>{tables.instruments().camera_height_bounds}},
    };
    if(ground_designation) context.tracking_target_q8.emplace(vec3<int32_t>{designated_point});
    else if(seeker.guidance && air_simulation.aircraft()[*seeker.guidance]) context.tracking_target_q8.emplace(vec3<int32_t>{air_simulation.aircraft()[*seeker.guidance]->flight.pose.position});
    else if(radar.selected && air_simulation.aircraft()[*radar.selected]) context.tracking_target_q8.emplace(vec3<int32_t>{air_simulation.aircraft()[*radar.selected]->flight.pose.position});
    if(player_disabled) context.impact_target_q8.emplace(vec3<int32_t>{vec3<uint32_t>{player.integer_position} * static_cast<uint32_t>(tfx::actors::position_unit)});
    else if(impact_aircraft && air_simulation.aircraft()[*impact_aircraft]) context.impact_target_q8.emplace(vec3<int32_t>{air_simulation.aircraft()[*impact_aircraft]->flight.pose.position});
    if(context.impact_target_q8) context.observed_target_q8.emplace(vec3<int32_t>{*context.impact_target_q8});
    else if(seeker.guidance && air_simulation.aircraft()[*seeker.guidance]) context.observed_target_q8.emplace(vec3<int32_t>{air_simulation.aircraft()[*seeker.guidance]->flight.pose.position});
    else if(context.tracking_target_q8) context.observed_target_q8.emplace(vec3<int32_t>{*context.tracking_target_q8});
    if(camera_missile) if(auto const shot{projectiles.projectiles().find(*camera_missile)}; shot != projectiles.projectiles().end() && !shot->second->spent) context.missile.emplace(tfx::cockpit::missile_camera_pose{
      .position_q8{vec3<int32_t>{shot->second->state.position}},
      .angles{vec3<tfx::math::angle>{shot->second->state.angles}},
    });
    return context;
  }};
  auto const forward_pose{[&] {
    auto const context{camera_context()};
    tfx::cockpit::view_pose pose{
      .anchor{vec3<int32_t>{context.position}},
      .position_q16{vec3<int32_t>{vec3<uint32_t>{context.position_q8} * 256u}},
      .angles{static_cast<tfx::math::angle>(-player.angles.x),static_cast<tfx::math::angle>(-player.angles.y),static_cast<tfx::math::angle>(-player.angles.z)},
    };
    pose.matrix = tfx::math::view_rotation_words(pose.angles);
    return pose;
  }};
  auto const flight_view{[&] { return forward_pose().camera(cockpit_frame.projection_origin(view_index(),cockpit_position.value())); }};
  std::vector<vec3<int32_t>> map_targets;
  for(auto const &target : mission_setup.targets) map_targets.emplace_back(target.position);
  auto const apply_selection{[&](tfx::weapons::selection_change const &change) {
    if(change.clear_contact) radar.selected.reset();
    if(change.clear_tracking) { seeker.tracking.reset(); seeker.guidance.reset(); ground_designation.reset(); mobile_designation.reset(); }
  }};
  auto const select_weapon{[&](tfx::weapons::weapon_role const role) {
    if(player.collision) return;
    if(armament.selected == tfx::weapons::no_pylon) armament.selected = 0;
    aiming_mode = role == tfx::weapons::weapon_role::ground ? tfx::cockpit::aiming_mode::ground : tfx::cockpit::aiming_mode::air;
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
        .enemy_pool{pool == 0},
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
    auto const pose{forward_pose()};
    auto const origin{cockpit_frame.projection_origin(view_index(),cockpit_position.value())};
    tfx::render::point_projection const projection{
      .matrix{mat3<int32_t>{pose.matrix}},
      .position_q16{vec3<int32_t>{pose.position_q16}},
      .origin{static_cast<int16_t>(origin.x),static_cast<int16_t>(origin.y)},
    };
    tfx::sensors::advance_air_lock(seeker,radar,radar_actors,tables.weapons[weapon],{
      .position{vec3<int32_t>{player.integer_position}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .elapsed{elapsed},
      .guns{armament.guns},
      .sensor_suppressed{defences.stealth},
      .centre{vec2<int16_t>{projection.origin}},
      .project{[&](vec3<int32_t> const &position) {
        if(auto const point{projection.integer(position)}) return vec2<int16_t>{*point};
        return vec2<int16_t>{-1,-1};
      }},
    });
  }};
  auto const restart{[&]{
    ground = initial_ground;
    ground_zone = -1;
    simple_controls = {};
    simple_controls.source = preferences.control;
    mouse_control = {};
    mission_time.reset();
    mission_progress.reset();
    engagement = {};
    launch_warning = nullptr;
    result_evaluated = false;
    campaign = initial_campaign;
    for(auto const name : {"a2akills","a2gkills","num_miss","num_hours","miss_val","score","fmobile_down"}) campaign.try_emplace(name,0);
    player = {};
    cannon = {};
    player_damage = {};
    g_effects = {};
    display_selection = instrument_setup.displays;
    aiming.reset_tracking();
    player_damage.systems = instrument_setup.systems;
    ground_target_page = 0;
    fuel_display = instrument_setup.fuel;
    defences = initial_defences;
    armament.pylons = initial_stores;
    armament.selected = 0;
    armament.select(mission_setup.aircraft == tfx::flight::player_aircraft::nighthawk ? tfx::weapons::weapon_role::ground : tfx::weapons::weapon_role::air,false);
    armament.guns = true;
    aiming_mode = tfx::cockpit::aiming_mode::navigation;
    refuelling.reset();
    landing.reset();
    ejection.reset();
    automatic_landing = {};
    stick_pressure = true;
    simple_body = simple_mode;
    player_visual = aircraft_visual;
    scene.show_actor(pilot_visual,false);
    for(auto const handle : {crashes.land,crashes.water,crashes.contact}) scene.show_actor(handle,false);
    impact_projection.reset();
    radio.clear();
    camera_missile.reset();
    impact_aircraft.reset();
    radar = {};
    seeker = {};
    designator = {};
    designator_view = false;
    views = tfx::cockpit::view_control{};
    view_motion = tfx::cockpit::view_camera{};
    view_pan = 0;
    cockpit_position.move_to(instrument_setup.offset);
    ground_designation.reset();
    mobile_designation.reset();
    radiation_cursor = 0;
    player.aircraft = mission_setup.aircraft;
    tfx::flight::loadout mounted;
    auto const &airframe{tables.aerodynamic_airframes.at(std::to_underlying(player.aircraft) - 1)};
    for(unsigned int slot{0}; slot != mounted.size(); ++slot) {
      auto const &pylon{armament.pylons[slot]};
      if(!pylon.count || pylon.weapon == tfx::weapons::empty_pylon) continue;
      auto const &weapon{tables.weapons.at(pylon.weapon)};
      mounted[slot] = {
        .position{vec3d{airframe.stores_and_mounts.mounts[slot]}},
        .properties{
          .mass_kg{weapon.mass},
          .drag{weapon.drag},
          .fuel_tank{weapon.role == tfx::weapons::weapon_role::external_tank},
        },
        .occupied{true},
      };
    }
    player_flight.initialise(airframe,mounted,{
      .position{vec3<int32_t>{mission_setup.start.position}},
      .angles{vec3<tfx::math::angle>{mission_setup.angles}},
      .model{preferences.model},
      .player_route_points{static_cast<unsigned int>(player_route.size())},
      .ground_elevation_steps{ground.height},
      .landed{mission_setup.start.landed},
      .wind{
        .terrain_wind_boost{environment.lighting.cloud_layer},
        .weather_wind_boost{environment.lighting.storm},
      },
      .surface_celsius{surface_celsius()},
    },mission_setup.speed_factor,wind_parameters,player_damage,air_simulation.random_stream());
    player.crashing = preferences.effects.crashing != 0;
  }};
  auto const flight_audio{[&] {
    return audio::flight_audio_state{
      .throttle{player.throttle},
      .engines_running{player.left_engine || player.right_engine},
      .inhibited{ejection.value().stage != flight::ejection_stage::cockpit},
      .collision{player.collision != 0},
      .aircraft_disabled{player_disabled}
    };
  }};
  auto const advance_world{[&](tfx::flight::flight_controls const &controls, tfx::simulation::timer_ticks const elapsed, double const physics_seconds, bool const fire = false, bool const release_store = false, bool const joystick_fire = false) {
    if(mission_progress.ended) return;
    for(auto const index : mission_time.begin_frame()) {
      radio.show(mission_setup.messages[index].text);
    }
    launch_elapsed = elapsed;
    if(sound) { sound->advance(elapsed);sound->update_flight(flight_audio()); }
    auto const previous{vec3<int32_t>{player.integer_position}};
    bool const previous_gear{player.gear_down}, previous_chute{player.brake_chute};
    auto const fire_gun{[&](bool const trigger) {
      if(auto const shot{tfx::weapons::fire_cannon(cannon,{
        .aircraft{player.aircraft},
        .position{vec3<int32_t>{player.integer_position}},
        .angles{vec3<tfx::math::angle>{player.angles}},
        .speed{player.fixed_speed},
        .trigger{trigger},
        .gun_mode{armament.guns},
        .flaps_available{player_damage.condition(tfx::flight::aircraft_system::flaps) != tfx::flight::system_condition::unavailable},
        .communications_available{player_damage.condition(tfx::flight::aircraft_system::communications) != tfx::flight::system_condition::unavailable},
        .inhibited{refuelling.value().phase != 0},
        .crashed{player.collision != 0},
        .ejected{player_disabled || ejected()},
        .landed{player.landed},
      },tables.cannon_mounts,air_simulation.random_stream())}) projectiles.launch(*shot);
    }};
    if(joystick_fire && armament.guns && !player_disabled && !ejected() && !player.collision && !player.landed) {
      auto const condition{player_damage.condition(tfx::flight::aircraft_system::weapons)};
      fire_gun(condition != tfx::flight::system_condition::failed && (condition != tfx::flight::system_condition::intermittent || air_simulation.random_stream().next() <= 3000));
    }
    if(release_store && !ejected() && !player_disabled && !armament.guns && armament.selected >= 0 && armament.selected < tfx::weapons::cannon_pylon && !player.landed) {
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
          .inhibited{player.collision != 0 || refuelling.value().phase != 0},
        },tables.store_mounts[std::to_underlying(player.aircraft) - 1],change,[&](auto const &shot) { projectiles.launch(shot); });
        apply_selection(change);
      }
    }
    for(unsigned int slot{0}; slot != physical_player.mounted_stores.size(); ++slot) physical_player.mounted_stores[slot].occupied = armament.pylons[slot].count != 0 && armament.pylons[slot].weapon != tfx::weapons::empty_pylon;
    physical_player.stores = tfx::flight::accumulate_stores(physical_player.aircraft.stores_and_mounts.stores,physical_player.mounted_stores);
    tfx::flight::aerodynamic_navigation_context navigation{
      .route_cells{player_route},
    };
    if(radar.selected && air_simulation.aircraft()[*radar.selected]) {
      auto const &target{air_simulation.aircraft()[*radar.selected]->flight.pose};
      navigation.followed_aircraft.emplace(tfx::flight::aerodynamic_follow_target{
        .position_q8{vec3<int32_t>{target.position}},
        .speed_q16{target.speed},
      });
    }
    auto const update{player_flight.advance(player_damage,air_simulation.random_stream(),wind_parameters,{
      .runway{landing.value()},
      .physics{
        .input{
          .source{simple_controls.source},
          .keys{simple_controls.keys},
          .joystick{vec2<int16_t>{simple_controls.joystick}},
          .mouse{vec2<int16_t>{mouse_control.position}},
          .alt{simple_controls.alt},
          .accelerate{controls.accelerate},
          .decelerate{controls.decelerate},
        },
        .seconds{physics_seconds},
        .ground_elevation_steps{ground.height},
        .surface_celsius{surface_celsius()},
        .refuelling_phase{refuelling.value().phase},
        .terrain_present{ground.present},
        .rough_surface{ground_zone == 2},
        .carrier_surface{ground_zone == 3},
        .wheel_brakes{player.wheel_brake},
        .gear_damage_enabled{preferences.effects.gear_damage != 0},
        .precipitation{preferences.effects.precipitation != 0},
        .crashing{player.crashing},
        .stick_pressure{stick_pressure},
        .wind_enabled{preferences.effects.wind != 0},
        .terrain_wind_boost{environment.lighting.cloud_layer},
        .weather_wind_boost{environment.lighting.storm},
        .navigation{navigation},
        .recovery_available{preferences.effects.recovery != 0},
        .ejected{player_disabled || ejected()},
        .approach_reference_enabled{landing.value().enabled},
      },
      .basic_controls{controls},
      .elapsed{elapsed},
      .surface_type{ground_zone},
      .pilot_terrain_type{scene.terrain_type(player.integer_position)},
      .refuel_per_update{tables.refuel_parameters().fuel_per_update},
      .aircraft_disabled{player_disabled},
      .water_world{environment.lighting.water_world},
    })};
    if(preferences.effects.g_force != tfx::configuration::g_effects::none) tfx::render::advance_g_effects(g_effects,simple_player.displayed_g_load,preferences.effects.g_force,elapsed);
    else g_effects = {};
    bool const landing_callback{update.callback == tfx::flight::player_callback::automatic_landing};
    for(auto const id : update.gear_sounds) sample(audio::sample_priority::urgent,id);
    for(auto const change : update.aerodynamic.recovery_changes) if(change == flight::aerodynamic_recovery_change::engaged) sample(audio::sample_priority::urgent,audio::sample_id::recovery);
    if(update.refuel_afterburner_warning) radio.show(tables.refuel_parameters().afterburner_message);
    if(update.aerodynamic.descent_warning) radio.show(tables.instruments().descent_warning);
    for(auto const entry : update.model_entries) scene.actor_event(player_visual,entry);
    for(auto const event : update.aerodynamic.afterburner) {
      reheat_sound(event);
      if(event == tfx::flight::afterburner_change::started) scene.actor_event(player_visual,9);
      else if(event == tfx::flight::afterburner_change::stopped) scene.actor_event(player_visual,10);
    }
    for(auto const event : update.landing.ordered) {
      if(event == flight::automatic_landing_event::gear_lowered || event == flight::automatic_landing_event::gear_raised) sample(audio::sample_priority::normal,audio::sample_id::gear);
      else if(event == flight::automatic_landing_event::afterburner_stopped) sample(audio::sample_priority::normal,audio::sample_id::afterburner_stop);
      else if(event == flight::automatic_landing_event::stopped) sample(audio::sample_priority::urgent,audio::sample_id::landing_stopped);
      if(event == tfx::flight::automatic_landing_event::gear_lowered) scene.actor_event(player_visual,3);
      else if(event == tfx::flight::automatic_landing_event::gear_raised) scene.actor_event(player_visual,4);
      else if(event == tfx::flight::automatic_landing_event::afterburner_stopped) scene.actor_event(player_visual,10);
    }
    campaign["score"] = std::bit_cast<int32_t>(static_cast<uint32_t>(campaign["score"]) + static_cast<uint32_t>(update.landing.score_change));
    if(update.pilot_fatal) {
      mission_progress.outcome = tfx::missions::session_outcome::aircraft_lost;
      mission_progress.status = tfx::missions::session_status::aircraft_lost;
    }
    if(update.pilot_ended) mission_progress.ended = true;
    if(!ejected()) {
      if(!landing_callback && std::ranges::find(update.model_entries,player.gear_down ? 3u : 4u) == update.model_entries.end() && previous_gear != player.gear_down && player_damage.condition(tfx::flight::aircraft_system::landing_gear) != tfx::flight::system_condition::failed) {
        player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::landing_gear)] = player.gear_down ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
        scene.actor_event(player_visual,player.gear_down ? 3u : 4u);
      }
      if(previous_chute && !player.brake_chute && std::ranges::find(update.model_entries,16u) == update.model_entries.end()) scene.actor_event(player_visual,16);
    }
    // Native 0x70ec8 follows player physics; the SSD event switches actors here,
    // leaving the first launch update to the next flight frame.
    if(ejection.advance_aircraft(player.position,body_basis(),player.fixed_speed,elapsed)) player_visual = pilot_visual;
    if(ejection.value().stage == tfx::flight::ejection_stage::pilot) scene.place_actor(aircraft_visual,vec3d{ejection.value().aircraft_position_q8} / tfx::actors::position_unit,ejection.value().aircraft_orientation.angles());
    // Native 0x86898 fires the held Space key after its player-physics callback, before other actors update.
    // Original nonzero checks read FLP and COM slots, despite their unrelated display names.
    fire_gun(fire);
    std::vector<tfx::missions::target_life> targets;
    for(auto const &target : mission_setup.targets) targets.push_back(scene.terrain_intact(static_cast<unsigned int>(target.position.x / tfx::world::cell_units),static_cast<unsigned int>(target.position.z / tfx::world::cell_units)) ? tfx::missions::target_life::alive : tfx::missions::target_life::dead);
    for(auto const &event : mission_progress.begin_frame({
      .mission_time{mission_time.elapsed()},
      .elapsed{elapsed},
      .targets{targets},
      .landed{player.landed},
      .speed{player.fixed_speed},
      .arcade{!campaign_flight || (campaign.contains("arcade") && campaign.at("arcade") != 0)},
    })) {
      if(auto const *notice{std::get_if<missions::progress_notice>(&event)}) radio.show(notice->kind == missions::notice_kind::target_destroyed ? *mission_setup.targets[notice->target].text : *mission_setup.completion->text);
      else {
        if(sound) sound->music_cue(audio::music_cue_id::mission_complete);
        sample(audio::sample_priority::urgent,audio::sample_id::mission_complete);
      }
    }
    air_world.player = tfx::actors::air_contact{
      .position{vec3<int32_t>{vec3<long double>{player.position} * tfx::actors::position_unit}},
      .angles{vec3<tfx::math::angle>{player.angles}},
      .speed{std::bit_cast<int32_t>(static_cast<uint32_t>(player.fixed_speed) << tfx::actors::speed_fraction_bits)},
    };
    scene.place_actor(player_visual,vec3d{player.position},player.angles);
    tfx::flight::repair_systems(player_damage,elapsed);
    advance_actors(elapsed);
    auto const contact_source{player_visual};
    auto const contact_damage{scene.actor_impact_damage(contact_source)};
    {
      // Native 0x72018 updates actors before collecting contacts; the next flight frame consumes this surface result.
      bool const previously_destroyed{scene.actor_destroyed(player_visual)};
      bool const contact_explosion{player_visual == crashes.contact};
      if(previously_destroyed && !contact_explosion) scene.actor_event(player_visual,0);
      auto const response{[&](uint16_t const cost) { scene.apply_actor_contact_damage(contact_source,cost);damage_player(100); }};
      ground.present = false;
      ground_zone = -1;
      auto const collect{[&](tfx::world::instance_result const &contact) {
        if(contact.zone != -1) ground_zone = contact.zone;
        if(contact.surface_present) { ground.present = true; ground.height = contact.surface_height; }
      }};
      for(auto const handle : fixed_scenery) collect(scene.collide_actor(handle,previous,player.integer_position,contact_damage,response,damage_player,true));
      collect(scene.collide_terrain(previous,player.integer_position,contact_damage,true,response));
      // Native 0x7c724 queries nearby mobile assemblies after the terrain, including carrier decks.
      auto const region{tfx::actors::nearby_surface_region(previous,player.integer_position)};
      for(auto const &actor : surface_actors) if(!(actor.state.pose.flags & std::to_underlying(tfx::actors::surface_flag::retired)) && region.contains(actor.state.pose.position)) collect(scene.collide_actor(actor.visual,previous,player.integer_position,contact_damage,response,damage_player,true));
      auto const contact{tfx::world::resolve_player_contact({
        .previously_destroyed{previously_destroyed},
        .destroyed{scene.actor_destroyed(player_visual)},
        .contact_explosion{contact_explosion},
        .pilot_active{ejection.value().pilot.phase != tfx::flight::pilot_phase::inactive},
      })};
      if(contact.collision) player.collision = 1;
      if(contact.release_motion_hold) player.frozen = false;
      if(contact.action == tfx::world::player_contact_action::restore_destroyed) scene.actor_event(player_visual,17);
      else if(contact.action == tfx::world::player_contact_action::explode) {
        mission_progress.begin_contact_explosion();
        views.enqueue(tfx::cockpit::view_mode::unbanked_chase,player.fixed_speed);
        scene.show_actor(player_visual,false);
        player_visual = crashes.contact;
        scene.actor_event(player_visual,0);
        scene.place_actor(player_visual,vec3d{player.position},player.angles);
        sample(audio::sample_priority::normal,audio::sample_id::aircraft_explosion);
      }
    }
    // Native 0x71535 checks only the selected refueller after ordinary world contacts.
    bool const before_tanker{scene.actor_destroyed(player_visual)};
    if(auto const selected{refuelling.value().selected}) {
      unsigned int const index{tfx::actors::aircraft_per_side + *selected};
      if(air_simulation.aircraft()[index] && air_visuals[index]) {
        auto const response{[&](uint16_t const cost) { scene.apply_actor_contact_damage(contact_source,cost);damage_player(100); }};
        scene.collide_actor(*air_visuals[index],previous,player.integer_position,contact_damage,response,damage_player,true);
        if(!before_tanker && scene.actor_destroyed(player_visual)) {
          scene.actor_event(player_visual,17);
          fatal_aircraft(index,tfx::actors::air_loss_cause::collision);
        }
      }
    }
    {
      auto const loss{mission_progress.observe_player_loss({
        .fatal{scene.actor_destroyed(player_visual)},
        .collision{player.collision != 0},
        .elapsed{elapsed},
        .height{player.integer_position.y},
        .pilot_active{ejection.value().pilot.phase != tfx::flight::pilot_phase::inactive},
        .contact_explosion{player_visual == crashes.contact},
      })};
      if(loss.force_collision) player.collision = 1;
      if(loss.first_loss) {
        if(sound) sound->music_cue(audio::music_cue_id::aircraft_lost);
        scene.actor_event(player_visual,21);
        views.enqueue(tfx::cockpit::view_mode::impact_orbit,player.fixed_speed);
      }
      if(loss.explosion && sound) {
        if(loss.mayday) sound->sequence(audio::sample_priority::normal,{std::to_underlying(audio::sample_id::aircraft_explosion),std::to_underlying(audio::sample_id::mayday)});
        else sample(audio::sample_priority::normal,audio::sample_id::aircraft_explosion);
      }
      if(loss.first_impact) {
        bool const water_world{environment.lighting.water_world};
        auto const point{impact_projection ? impact_projection->integer(player.integer_position) : std::nullopt};
        auto const surface{tfx::world::classify_impact(renderer.output,point,water_world)};
        auto const appearance{tfx::world::select_crash_appearance(player.collision,scene.terrain_type(player.integer_position),surface,water_world)};
        scene.show_actor(player_visual,false);
        player_visual = appearance == tfx::world::crash_appearance::water ? crashes.water : crashes.land;
        scene.actor_event(player_visual,0);
        player.angles = {0,0,0};
        scene.place_actor(player_visual,vec3d{player.position},player.angles);
      }
    }
    projectiles.advance(elapsed,air_simulation.random_stream());
    if(scene.advance(elapsed).eject_player) ejection.request();
    cockpit_position.advance(tables.instruments().viewports[view_index()].bottom);
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
      auto const recovered{recovery.resolve({
        .outcome{mission_progress.outcome},
        .status{mission_progress.status},
        .safe{campaign.contains("safe") && campaign.at("safe") != 0},
      },{
        .ejected{ejected()},
        .fatal{ejection.value().pilot.fatal},
        .damaged{player_damage.accumulated != 0},
        .violations{mission_progress.violations},
        .region{tfx::missions::pilot_recovery_region(selected.world_name)},
        .start{mission_setup.start.position.x,mission_setup.start.position.z},
        .position{player.integer_position.x,player.integer_position.z},
      })};
      mission_progress.outcome = recovered.outcome;
      mission_progress.status = recovered.status;
      campaign["safe"] = recovered.safe;
      campaign["score"] = std::bit_cast<int32_t>(static_cast<uint32_t>(campaign["score"]) + static_cast<uint32_t>(mission_progress.return_score));
      campaign["outcome"] = std::to_underlying(mission_progress.outcome);
      campaign["status"] = std::to_underlying(mission_progress.status);
      mission_finish.execute(mission_progress.results,campaign);
      result_evaluated = true;
      std::cout << "Mission result: " << campaign["miss_val"] << "; score " << campaign["score"] << "; outcome " << campaign["outcome"] << std::endl;
    }
  }};
  if(!inspect || flight_steps) restart();
  if(sound && !inspect && !override_cell && !screenshot) sound->begin_flight(flight_audio());
  for(unsigned int step{0}; step != flight_steps; ++step) {
    advance_world({},4,static_cast<double>(4 * .02f));
    finish_world(4);
  }
  // Native 0x72588 resumes the parser directly after FINISH and teardown.
  // A direct --mission launch keeps its standalone diagnostic result display.
  if(campaign_flight && result_evaluated) return flight_result::finished;
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
  auto const draw_instruments{[&](std::optional<std::string> const &radio_window) {
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
    state.threat = radar.hostile_nearby;
    state.fire_permission_notice = engagement.notice_frames != 0;
    if(launch_warning) state.tracked_weapon_category = tables.weapons[launch_warning->state.weapon].category;
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
    readings.engine_load = {physical_player.powerplant.engine_factor.x,physical_player.powerplant.engine_factor.y};
    auto const &targets{physical_player.manual.controls.autopilot};
    readings.controls = {
      .trailing_edge_flap{physical_player.manual.flap_fraction},
      .leading_edge_flap{physical_player.surfaces.automatic_flap_fraction},
      .thrust_vector{vec2d{physical_player.powerplant.nozzle_angles}},
      .autopilot{
        .enabled{targets.enabled},
        .mode{static_cast<tfx::cockpit::autopilot_mode>(targets.mode)},
        .heading{targets.heading},
        .waypoint{physical_player.autopilot.navigation.route_index},
        .height{targets.down_metres},
        .speed{targets.metres_per_second},
      },
      .configuration{static_cast<tfx::cockpit::flight_configuration>(physical_player.autopilot.recovery.configuration)},
    };
    readings.inventory = &armament;
    readings.confirmed_target = seeker.guidance.has_value() || ground_designation.has_value();
    state.position = vec3<int32_t>{player.integer_position};
    state.ticks = mission_time.elapsed();
    state.clock_offset = static_cast<uint32_t>(mission_setup.clock);
    state.elapsed = launch_elapsed;
    state.chaff = defences.chaff;
    state.flares = defences.flares;
    state.ecm = defences.ecm;
    state.stealth = defences.stealth;
    state.stall_recovery = player.recovering;
    state.hook = player.arrestor_hook;
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
    if(result.threat_sound) sample(audio::sample_priority::urgent,audio::sample_id::threat);
  }};
  auto const draw_aiming{[&](tfx::render::camera const &view, bool const limited) {
    aiming.check_fuel(player.fuel);
    auto const fault{player_damage.condition(tfx::flight::aircraft_system::hud)};
    if(fault == tfx::flight::system_condition::failed || (fault == tfx::flight::system_condition::intermittent && (air_simulation.random_stream().next() & 1))) return;
    auto const offset{vec2<int16_t>{cockpit_position.value()}};
    unsigned int const weapon_index{armament.selected < 0 ? 0u : armament.pylons[static_cast<unsigned int>(armament.selected)].weapon};
    auto const &weapon{tables.weapons.at(weapon_index < tables.weapons.size() ? weapon_index : 0)};
    tfx::cockpit::weapon_display_state state{
      .mode{aiming_mode},
      .aircraft{player.aircraft},
      .weapon{weapon.label},
      .range{weapon.range},
      .category{weapon.category},
      .cannon{weapon_index == 0},
      .ammunition{cannon.ammunition},
      .air_lock{seeker.guidance.has_value()},
      .ground_lock{ground_designation.has_value()},
      .limited{limited},
      .elapsed{launch_elapsed},
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
    if(radar.selected && air_simulation.aircraft()[*radar.selected]) {
      auto const &actor{air_simulation.aircraft()[*radar.selected]->flight.pose};
      auto const profile{std::ranges::find(profiles,actor.profile_id,&tfx::actors::profile::id)};
      state.air_target.emplace(tfx::cockpit::air_target_cue{
        .reading{
          .name{profile->name},
          .position_q8{vec3<int32_t>{actor.position}},
          .heading{actor.angles.y},
          .speed_q16{actor.speed},
        },
        .orientation{player.orientation},
        .projected{vec2<int16_t>{seeker.projected}},
        .tracking_q8{vec2<int32_t>{seeker.reticle}},
        .acquiring{seeker.tracking.has_value()},
      });
    }
    if(refuelling.value().selected) {
      unsigned int const index{tfx::actors::aircraft_per_side + *refuelling.value().selected};
      auto const &actor{air_simulation.aircraft()[index]->flight.pose};
      auto const profile{std::ranges::find(profiles,actor.profile_id,&tfx::actors::profile::id)};
      state.navigation_target.emplace(tfx::cockpit::air_target_cue{
        .reading{
          .name{profile->name},
          .position_q8{vec3<int32_t>{actor.position}},
          .heading{actor.angles.y},
          .speed_q16{actor.speed},
        },
        .orientation{player.orientation},
        // The original refuelling HUD precedes acquisition and shares its
        // retained projected point, independently of the selected actor data.
        .projected{vec2<int16_t>{seeker.projected}},
      });
    }
    auto const &pose{view_motion.last_pose()};
    tfx::render::point_projection const projection{
      .matrix{mat3<int32_t>{pose.matrix}},
      .position_q16{vec3<int32_t>{pose.position_q16}},
      .origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)},
    };
    if(state.mode == tfx::cockpit::aiming_mode::navigation && landing.value().enabled) {
      state.landing.emplace(landing.advance(player.integer_position,false,[&](auto const &position) {
        if(auto const point{projection.integer(position)}) return tfx::flight::landing_projection{
          .valid{true},
          .point{vec2<int16_t>{*point}},
        };
        return tfx::flight::landing_projection{};
      }));
      if(state.landing->speed_request) radio.show(tables.instruments().landing_radio_messages[std::to_underlying(tfx::flight::landing_radio::approach_speed)]);
    }
    if(state.mode == tfx::cockpit::aiming_mode::ground && ground_designation) state.ground_marker = projection.integer({designated_point.x >> 8,designated_point.y >> 8,designated_point.z >> 8});
    if(state.mode == tfx::cockpit::aiming_mode::navigation || state.cannon || weapon.category == tfx::weapons::bomb_impact_category) {
      vec3<int32_t> const origin{vec3<uint32_t>{player.integer_position} * static_cast<uint32_t>(tfx::actors::position_unit)};
      auto const anchor{tfx::math::place_anchor(origin,player.angles,tables.sight_mount(player.aircraft,armament.selected))};
      auto const project_prediction{[&](vec3<int32_t> const &position) {
        if(auto const point{projection.integer({position.x >> 8,position.y >> 8,position.z >> 8})}) return vec2<int16_t>{*point};
        return vec2<int16_t>{-1,-1};
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
    if(!inspect && !result_evaluated) update_refuelling();
    if(!inspect && !designator_view) {
      if(!tables.instruments().viewports[view_index()].panel.empty()) cockpit_position.move_to(cockpit_frame.clamp(view_index(),cockpit_position.value()));
      views.offset(cockpit_position.value());
      if(!view_motion.advance(views,camera_context())) throw std::runtime_error{"unimplemented flight camera"};
      auto const entry{view_motion.last_pose().player_model_entry};
      scene.show_actor(player_visual,entry.has_value());
      if(entry) scene.actor_event(player_visual,*entry);
    } else scene.show_actor(player_visual,false);
    if(ejection.value().stage == tfx::flight::ejection_stage::pilot) scene.show_actor(aircraft_visual,true);
    auto view{inspect ? tfx::render::inspection_camera(position,heading,pitch) : designator_view ? flight_view() : view_motion.last_pose().camera(cockpit_frame.projection_origin(view_index(),cockpit_position.value()))};
    if(!inspect && designator_view) {
      double constexpr radians_per_angle{2 * std::numbers::pi / 65536};
      view = tfx::render::inspection_camera(vec3d{designator.camera},designator.heading * radians_per_angle,-tfx::math::signed_word(designator.pitch) * radians_per_angle);
    }
    if(!inspect) {
      auto const lighting{palette_lighting.advance({
        .camera_y{designator_view ? designator.camera.y : view_motion.last_pose().anchor.y},
        .pitch{player.angles.x},
        .roll{player.angles.z},
        .view{designator_view ? tfx::cockpit::view_mode::designator : views.value().current},
        .hud_green{static_cast<uint8_t>(hud_green)},
        .normal_changed{palette_selection.value().normal_changed},
        .blackout{g_effects.mode},
        .blackout_level{g_effects.blackout_level},
        .redout_level{g_effects.redout_level},
      })};
      if(lighting.changed) palette_selection.invalidate_normal();
      if(auto const upload{palette_selection.advance({
        .view{designator_view ? tfx::cockpit::view_mode::designator : views.value().current},
        .projectiles_present{!projectiles.projectiles().empty()},
        .infrared_available{!environment.lighting.infrared_palette_name.empty()},
        .night{(environment.lighting.status & tfx::world::night_status) != 0},
        .night_vision{night_vision},
      })}) {
        if(*upload == tfx::render::palette_bank::normal) colours = tfx::render::expand_dac_palette(palette_lighting.colours());
        frame_colours = *upload == tfx::render::palette_bank::infrared ? &infrared_colours : &colours;
      }
    }
    if(!inspect) {
      tfx::render::point_projection projected_view{
        .matrix{},
        .position_q16{vec3<int32_t>{vec3<uint32_t>{vec3<int64_t>{view.position * 65536}}}},
        .origin{static_cast<int16_t>(view.projection_origin.x),static_cast<int16_t>(view.projection_origin.y)},
      };
      // Recover the exact Q15 rows for native cameras; the designator's current camera supplies its own rows.
      for(unsigned int row{0}; row != 3; ++row) {
        auto const &axis{row == 0 ? view.right : row == 1 ? view.down : view.forward};
        for(unsigned int column{0}; column != 3; ++column) projected_view.matrix.data[row * 3 + column] = static_cast<int32_t>(axis[column] * tfx::math::matrix_unit);
      }
      impact_projection.emplace(projected_view);
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
      auto const callback{tables.instruments().viewports[view_index()].callback_file};
      auto const radio_window{callback == 0x80704 ? std::optional<std::string>{} : radio.advance(launch_elapsed)};
      if(!designator_view && (callback == 0x806dc || callback == 0x80718 || callback == 0x80758)) draw_aiming(view,callback != 0x80758);
      if(!designator_view && view_index() == tfx::cockpit::forward_cockpit) {
        cockpit_frame.paint(renderer.output,view_index(),cockpit_position.value());
        draw_instruments(radio_window);
      } else if(!designator_view && callback == 0x80704) cockpit_frame.paint(renderer.output,view_index(),cockpit_position.value());
      else {
        if(!designator_view && callback == 0x80794) external_instruments.draw(renderer,{
          .height{player.position.y},
          .speed{player.fixed_speed},
          .heading{player.angles.y},
        });
        if(radio_window) instruments.draw_radio(renderer,*radio_window);
      }
      // The separate designator-view labels await their native camera callback.
      uint8_t constexpr hud_colour{15};
      if(designator_view) {
        renderer.line({150,100},{170,100},hud_colour);
        renderer.line({160,90},{160,110},hud_colour);
        renderer.text(100,150,ground_designation ? "DESIGNATED" : "Z TO DESIGNATE",hud_colour);
        renderer.text(100,160,std::format("ZOOM {}",designator.zoom),hud_colour);
      }
      if(paused) renderer.text(140,80,"PAUSED",hud_colour);
      engagement.finish_frame();
      launch_warning = projectiles.first_targeting_player();
      flight_frame = renderer.output;
      if(!designator_view && views.value().ready) {
        views.consume();
        cockpit_position.move_to(views.value().offset);
      }
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
    renderer.output.screenshot(*screenshot,*frame_colours);
    std::cout << "Initial scene screenshot: " << *screenshot << std::endl;
    return flight_result::finished;
  }
  std::unique_ptr<tfx::platform::window> owned_window;
  if(!shared_window) owned_window = std::make_unique<tfx::platform::window>(scale);
  auto &window{shared_window ? *shared_window : *owned_window};
  // Wayland maps the window after its first buffer: present before waiting for focus.
  window.present(renderer.output.colourise(*frame_colours));
  auto *const host{window.get()};
  std::optional<int> joystick;
  tfx::flight::joystick_buttons stick_buttons;
  auto const poll_stick{[&]() -> uint8_t {
    if(preferences.control != tfx::flight::control_source::joystick || arcade_mode) return 0;
    if(!joystick || !glfwJoystickPresent(*joystick)) {
      joystick.reset();
      for(int device{options.joystick ? static_cast<int>(*options.joystick) : GLFW_JOYSTICK_1}; device <= (options.joystick ? static_cast<int>(*options.joystick) : GLFW_JOYSTICK_LAST); ++device) {
        int count{0};
        if(glfwJoystickPresent(device) && glfwGetJoystickAxes(device,&count) && count >= 2) { joystick = device;break; }
      }
    }
    if(!joystick) { simple_controls.source = tfx::flight::control_source::keyboard;simple_controls.joystick = {0,0};return 0; }
    simple_controls.source = tfx::flight::control_source::joystick;
    int count{0};
    auto const *axes{glfwGetJoystickAxes(*joystick,&count)};
    if(!axes || count < 2) return 0;
    simple_controls.joystick = tfx::flight::joystick_axes({axes[0],axes[1]},preferences.joystick_scale);
    auto const *buttons{glfwGetJoystickButtons(*joystick,&count)};
    uint8_t mask{0};
    for(int index{0}; buttons && index != std::min(count,4); ++index) if(buttons[index] == GLFW_PRESS) mask |= static_cast<uint8_t>(1u << index);
    return mask;
  }};
  // Arcade consumes relative mouse-style input; Simple has no mouse law.
  if((arcade_mode && simple_controls.source == tfx::flight::control_source::joystick) || (simple_mode && simple_controls.source == tfx::flight::control_source::mouse)) simple_controls.source = tfx::flight::control_source::keyboard;

  double previous_time{glfwGetTime()}, title_time{previous_time}, last_mouse_x{0}, last_mouse_y{0}, timer_fraction{0};
  unsigned int frames{0}, interval_frames{0};
  bool captured{false}, mouse_started{false}, store_trigger{false};
  std::array<bool,GLFW_KEY_LAST + 1> held{false};
  tfx::simulation::timer_counter counter{0};
  tfx::simulation::flight_clock flight_clock{counter};
  flight_clock.begin({
    .model{preferences.model},
  });
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
    auto const pressed{[&](int const key){
      bool const active{down(key)}, edge{active && !held[static_cast<unsigned int>(key)]};
      held[static_cast<unsigned int>(key)] = active;
      return edge;
    }};
    if((inspect || result_evaluated) && pressed(GLFW_KEY_ESCAPE)) break;
    if((down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT)) && pressed(GLFW_KEY_Q)) break;
    if(result_evaluated && (pressed(GLFW_KEY_ENTER) || pressed(GLFW_KEY_KP_ENTER))) break;
    if(!inspect && !result_evaluated && pressed(GLFW_KEY_GRAVE_ACCENT)) {
      captured = mouse_started = false;
      preferences.hud_green = static_cast<uint16_t>(hud_green);
      auto const action{configure_flight(window,tables,preferences,options.data_directory,renderer.output,*frame_colours,sound)};
      if(action == tfx::presentation::configuration_action::enrol) return flight_result::enrol;
      if(action == tfx::presentation::configuration_action::quit) break;
      simple_mode = preferences.model == tfx::simulation::flight_model::simple;
      arcade_mode = preferences.model == tfx::simulation::flight_model::arcade;
      player_flight.select_model(preferences.model);
      air_world.model = preferences.model;
      simple_controls.source = preferences.control;
      player.crashing = preferences.effects.crashing != 0;
      environment.lighting.status = tfx::world::apply_detail_status(environment.lighting.status,preferences.detail);
      if(preferences.effects.g_force == tfx::configuration::g_effects::none) { g_effects = {};palette_lighting.flash(tfx::render::lighting_stages); }
      palette_selection.invalidate_normal();
      mouse_control = {};
      pitch_input = roll_input = 0;
      store_trigger = false;
      held.fill(false);
      flight_clock.resume(counter,{
        .model{preferences.model},
      });
      previous_time = title_time = glfwGetTime();
      interval_frames = 0;
      continue;
    }
    if(!inspect && !result_evaluated && pressed(GLFW_KEY_P)) paused = !paused;
    uint8_t const stick_mask{!inspect && !paused && !result_evaluated ? poll_stick() : uint8_t{0}};
    bool const capture{inspect ? glfwGetMouseButton(host,GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS : simple_controls.source == tfx::flight::control_source::mouse && !paused && !result_evaluated};
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
      if(pressed(GLFW_KEY_ESCAPE)) {
        auto const result{ejection.escape(player.integer_position,player.angles,player.fixed_speed)};
        if(result.disable_refuelling) refuelling.disengage();
        if(result.fixed_camera) views.fixed_position(*result.fixed_camera);
        for(auto const &event : result.events) {
          if(event.kind == tfx::flight::ejection_event_kind::player_model) scene.actor_event(player_visual,event.argument);
          else if(event.kind == tfx::flight::ejection_event_kind::camera) views.enqueue(static_cast<tfx::cockpit::view_mode>(event.argument),player.fixed_speed);
          else if(event.kind == tfx::flight::ejection_event_kind::sample && sound) sound->sequence(audio::sample_priority::normal,{event.argument,event.argument});
          else if(event.kind == tfx::flight::ejection_event_kind::music_cue && sound) sound->music_cue(static_cast<uint8_t>(event.argument));
        }
        if(result.end_flight) {
          mission_progress.ended = true;
          finish_world(0);
          continue;
        }
      }
      std::array<std::pair<int,tfx::flight::defensive_key>,6> constexpr defensive_bindings{{
        {GLFW_KEY_E,tfx::flight::defensive_key::ecm},
        {GLFW_KEY_S,tfx::flight::defensive_key::stealth},
        {GLFW_KEY_INSERT,tfx::flight::defensive_key::chaff},
        {GLFW_KEY_KP_0,tfx::flight::defensive_key::chaff},
        {GLFW_KEY_DELETE,tfx::flight::defensive_key::flare},
        {GLFW_KEY_KP_DECIMAL,tfx::flight::defensive_key::flare},
      }};
      for(auto const &[key,action] : defensive_bindings) if(pressed(key)) {
        auto const effects{tfx::flight::press_defensive_key(defences,action,{
          .aircraft{player.aircraft},
          .ejecting{ejected()},
          .collision{player.collision != 0},
          .disabled{player_disabled},
          .afterburner{player.afterburner},
        })};
        if(effects.clear_targeting) { radar.selected.reset();seeker.tracking.reset();seeker.guidance.reset(); }
        if(effects.release) {
          tfx::weapons::actor_identity const owner{
            .pool{tfx::weapons::actor_pool::player},
          };
          projectiles.countermeasure(owner,actor_position(owner),effects.release->radar,effects.release->strength,air_simulation.random_stream());
        }
      }
      if(!ejected()) {
        tfx::flight::capture_shared_player(physical_player,simple_player,player_damage,simple_body);
        std::array<std::pair<int,tfx::flight::aerodynamic_pilot_key>,7> constexpr pilot_bindings{{
          {GLFW_KEY_6,tfx::flight::aerodynamic_pilot_key::cruise_speed},
          {GLFW_KEY_5,tfx::flight::aerodynamic_pilot_key::stick_pressure},
          {GLFW_KEY_7,tfx::flight::aerodynamic_pilot_key::waypoint},
          {GLFW_KEY_8,tfx::flight::aerodynamic_pilot_key::heading},
          {GLFW_KEY_9,tfx::flight::aerodynamic_pilot_key::track},
          {GLFW_KEY_0,tfx::flight::aerodynamic_pilot_key::autothrottle},
          {GLFW_KEY_A,tfx::flight::aerodynamic_pilot_key::toggle_autopilot},
        }};
        for(auto const &[key,action] : pilot_bindings) if(pressed(key)) {
          auto const events{tfx::flight::press_aerodynamic_pilot_key(physical_player,player_damage,stick_pressure,action,{
            .ground_elevation_steps{ground.height},
            .terrain_present{ground.present},
            .ejected{player_disabled},
            .recovery_available{preferences.effects.recovery != 0},
          })};
          if(events.notice) radio.show(tables.instruments().pilot_notices[std::to_underlying(*events.notice)]);
          if(events.recovery.change == flight::aerodynamic_recovery_change::engaged) sample(audio::sample_priority::urgent,audio::sample_id::recovery);
          for(auto const event : events.recovery.afterburner) {
            reheat_sound(event);
            if(event == tfx::flight::afterburner_change::started) scene.actor_event(player_visual,9);
            else if(event == tfx::flight::afterburner_change::stopped) scene.actor_event(player_visual,10);
          }
          tfx::flight::publish_shared_player(simple_player,physical_player);
        }
        if(pressed(GLFW_KEY_TAB)) {
          auto &condition{player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::air_brake)]};
          auto const events{tfx::flight::toggle_aerodynamic_recovery(physical_player.autopilot.recovery,physical_player.manual.controls,physical_player.powerplant,condition,{
            .afterburner_stages{physical_player.aircraft.powerplant.afterburner_stages},
            .available{preferences.effects.recovery != 0},
            .crashed{player.collision != 0},
            .ejected{player_disabled},
            .landed{player.landed},
          })};
          if(events.change == flight::aerodynamic_recovery_change::engaged) sample(audio::sample_priority::urgent,audio::sample_id::recovery);
          for(auto const event : events.afterburner) {
            reheat_sound(event);
            if(event == tfx::flight::afterburner_change::started) scene.actor_event(player_visual,9);
            else if(event == tfx::flight::afterburner_change::stopped) scene.actor_event(player_visual,10);
          }
          tfx::flight::publish_shared_player(simple_player,physical_player);
        }
        if(pressed(GLFW_KEY_ENTER) || pressed(GLFW_KEY_KP_ENTER)) select_weapon(tfx::weapons::weapon_role::air);
        if(pressed(GLFW_KEY_BACKSPACE) || pressed(GLFW_KEY_O)) select_weapon(tfx::weapons::weapon_role::ground);
        if(pressed(GLFW_KEY_F)) { armament.guns = true;aiming_mode = tfx::cockpit::aiming_mode::navigation; }
        bool const replay_key{pressed(GLFW_KEY_L)};
        bool const auto_land_key{replay_key && (down(GLFW_KEY_LEFT_ALT) || down(GLFW_KEY_RIGHT_ALT))};
        if(pressed(GLFW_KEY_I) || pressed(GLFW_KEY_BACKSLASH) || auto_land_key) {
          std::vector<tfx::flight::landing_surface> carriers;
          // Native surface enumeration is descending by slot and allied-only.
          for(auto const &actor : surface_actors | std::views::reverse) {
            auto const &pose{actor.state.pose};
            if(pose.side != tfx::actors::allegiance::allied || (pose.flags & (std::to_underlying(tfx::actors::surface_flag::destroyed) | std::to_underlying(tfx::actors::surface_flag::retired)))) continue;
            if(auto const port{scene.actor_landing_port(actor.visual)}) carriers.push_back({
              .position_q8{vec3<int32_t>{pose.position}},
              .port{*port},
              .destroyed{scene.actor_destroyed(actor.visual)},
            });
          }
          tfx::flight::landing_selection result;
          if(auto_land_key) {
            if(!player.collision && !player_disabled && !player.landed && automatic_landing.phase == tfx::flight::automatic_landing_phase::inactive) {
              if(player_damage.condition(tfx::flight::aircraft_system::landing_gear) == tfx::flight::system_condition::failed) radio.show(tables.instruments().automatic_landing_gear_failure);
              else {
                result = landing.select_runway(actor_program.player_route,[&](auto const &cell) { return scene.terrain_landing_port(cell); },carriers);
                if(landing.value().enabled) {
                  views.enqueue(tfx::cockpit::view_mode::chase,player.fixed_speed);
                  automatic_landing.phase = tfx::flight::automatic_landing_phase::prepare;
                  result.navigation = true;
                  result.controls.emplace(tfx::flight::landing_controls{
                    .configuration{1},
                    .response{player.aircraft == tfx::flight::player_aircraft::nighthawk ? 1.0 : .5},
                    .pitch_response{preferences.model == simulation::flight_model::realistic ? .12 : .15},
                    .roll_response{preferences.model == simulation::flight_model::realistic ? .152 : .19},
                    .yaw_response{preferences.model == simulation::flight_model::realistic ? .024 : .03},
                  });
                }
              }
            }
          } else result = landing.toggle({
            .aircraft{player.aircraft},
            .crashed{player.collision != 0},
            .ejected{player_disabled || ejected()},
            .damaged{player_damage.accumulated != 0},
            .realistic{preferences.model == simulation::flight_model::realistic},
          },actor_program.player_route,[&](auto const &cell) { return scene.terrain_landing_port(cell); },carriers);
          if(result.afterburner_stop_sample) sample(audio::sample_priority::normal,audio::sample_id::afterburner_stop);
          if(result.music_cue && sound) sound->music_cue(static_cast<uint8_t>(*result.music_cue));
          if(result.navigation) { armament.guns = true;aiming_mode = tfx::cockpit::aiming_mode::navigation; }
          for(auto const message : result.messages) radio.show(tables.instruments().landing_radio_messages[std::to_underlying(message)]);
          if(result.waypoint) physical_player.autopilot.navigation.route_index = static_cast<int16_t>(*result.waypoint + 1);
          if(result.controls) {
            physical_player.autopilot.recovery.configuration = result.controls->configuration;
            physical_player.input_gains.joystick = result.controls->response;
            physical_player.input_gains.pitch = result.controls->pitch_response;
            physical_player.input_gains.roll = result.controls->roll_response;
            physical_player.input_gains.rudder = result.controls->yaw_response;
          }
        }
        if(pressed(GLFW_KEY_APOSTROPHE)) {
          auto const result{refuelling.toggle(static_cast<uint8_t>(std::to_underlying(aiming_mode)),false,player.collision != 0,player_disabled)};
          aiming_mode = static_cast<tfx::cockpit::aiming_mode>(result.weapon_mode);
          refuel_events(result.events);
        }
        if(replay_key && !down(GLFW_KEY_LEFT_ALT) && !down(GLFW_KEY_RIGHT_ALT) && !player.collision && !player_disabled) radio.replay();
        if(pressed(GLFW_KEY_C)) cycle_target();
        if(pressed(GLFW_KEY_1)) display_selection.cycle_left(!mission_setup.targets.empty());
        if(pressed(GLFW_KEY_2)) display_selection.cycle_centre(player.aircraft);
        if(pressed(GLFW_KEY_3)) {
          auto const *weapon{selected_weapon()};
          display_selection.cycle_right(player.aircraft,weapon ? weapon->category : tables.weapons[0].category);
        }
        if(pressed(GLFW_KEY_R)) display_selection.cycle_range();
        if(pressed(GLFW_KEY_N)) {
          if(down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT)) {
            if(!player.collision && !player_disabled) night_vision = !night_vision;
          } else if(!mission_setup.targets.empty()) ground_target_page = (ground_target_page + 1) % static_cast<unsigned int>(mission_setup.targets.size());
        }
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
      }
      auto const context{camera_context()};
      tfx::cockpit::view_key_context const view_keys{
        .crashed{player.collision != 0},
        .ejected{player_disabled || ejected()},
        .landing{automatic_landing.phase != tfx::flight::automatic_landing_phase::inactive},
        .shift{down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT)},
        .speed{player.fixed_speed},
        .position{vec3<int32_t>{player.integer_position}},
        .angles{vec3<tfx::math::angle>{player.angles}},
        .height_bounds{vec2<int32_t>{tables.instruments().camera_height_bounds}},
        .missile_available{context.missile.has_value()},
        .target_available{context.observed_target_q8.has_value()},
        .target_is_ground{ground_designation.has_value() && !seeker.guidance && !context.impact_target_q8},
        .tracking_available{context.tracking_target_q8.has_value()},
      };
      std::array<std::pair<int,tfx::cockpit::view_key>,10> constexpr view_bindings{{
        {GLFW_KEY_F1,tfx::cockpit::view_key::front},
        {GLFW_KEY_F2,tfx::cockpit::view_key::left},
        {GLFW_KEY_F3,tfx::cockpit::view_key::right},
        {GLFW_KEY_F4,tfx::cockpit::view_key::rear},
        {GLFW_KEY_F5,tfx::cockpit::view_key::chase},
        {GLFW_KEY_F6,tfx::cockpit::view_key::fly_past},
        {GLFW_KEY_F7,tfx::cockpit::view_key::tactical},
        {GLFW_KEY_F8,tfx::cockpit::view_key::missile},
        {GLFW_KEY_F9,tfx::cockpit::view_key::target},
        {GLFW_KEY_F10,tfx::cockpit::view_key::virtual_cockpit},
      }};
      views.offset(cockpit_position.value());
      for(auto const &[key,action] : view_bindings) if(pressed(key)) {
        views.press(action,view_keys);
        cockpit_position.move_to(views.value().offset);
        designator_view = false;
      }
      view_pan = view_keys.shift ? static_cast<uint16_t>((down(GLFW_KEY_LEFT) ? 1 : 0) | (down(GLFW_KEY_RIGHT) ? 2 : 0) | (down(GLFW_KEY_UP) ? 4 : 0) | (down(GLFW_KEY_DOWN) ? 8 : 0)) : 0;
      if(pressed(GLFW_KEY_COMMA) && designator_view && designator.zoom) --designator.zoom;
      if(pressed(GLFW_KEY_PERIOD) && designator_view && designator.zoom < 10) ++designator.zoom;
      designator_input = {
        .up{down(GLFW_KEY_UP)},
        .down{down(GLFW_KEY_DOWN)},
        .left{down(GLFW_KEY_LEFT)},
        .right{down(GLFW_KEY_RIGHT)},
      };
      if(pressed(GLFW_KEY_SPACE)) store_trigger = true;
      if(!player.collision && !player_disabled && !ejected()) {
        if(pressed(GLFW_KEY_PAGE_UP)) cockpit_position.raise();
        if(pressed(GLFW_KEY_PAGE_DOWN)) cockpit_position.lower();
        if(pressed(GLFW_KEY_LEFT_BRACKET)) player.left_engine = !player.left_engine;
        if(pressed(GLFW_KEY_RIGHT_BRACKET)) player.right_engine = !player.right_engine;
        if(!player.left_engine && !player.right_engine && player.afterburner) {
          physical_player.powerplant.stop_afterburner();
          player.afterburner = 0;
          scene.actor_event(player_visual,10);
        }
        if(automatic_landing.phase == tfx::flight::automatic_landing_phase::inactive && !physical_player.manual.controls.autopilot.enabled) {
          auto change{tfx::flight::afterburner_change::none};
          if(pressed(GLFW_KEY_KP_MULTIPLY)) change = down(GLFW_KEY_LEFT_ALT) || down(GLFW_KEY_RIGHT_ALT) ? physical_player.powerplant.decrease_afterburner() : physical_player.powerplant.increase_afterburner(physical_player.aircraft.powerplant.afterburner_stages);
          if(pressed(GLFW_KEY_MINUS) || pressed(GLFW_KEY_KP_SUBTRACT)) change = physical_player.powerplant.decrease_afterburner();
          player.afterburner = physical_player.powerplant.afterburner;
          player.throttle = physical_player.powerplant.throttle;
          reheat_sound(change);
          if(change == tfx::flight::afterburner_change::started) scene.actor_event(player_visual,9);
          else if(change == tfx::flight::afterburner_change::stopped) scene.actor_event(player_visual,10);
        }
        if(pressed(GLFW_KEY_G) && player_damage.condition(tfx::flight::aircraft_system::landing_gear) != tfx::flight::system_condition::failed) {
          sample(audio::sample_priority::normal,audio::sample_id::gear);
          player.gear_down = !player.gear_down;
          player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::landing_gear)] = player.gear_down ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
          scene.actor_event(player_visual,player.gear_down ? 3u : 4u);
        }
        if(pressed(GLFW_KEY_H) && !down(GLFW_KEY_LEFT_ALT) && !down(GLFW_KEY_RIGHT_ALT)) {
          player.arrestor_hook = !player.arrestor_hook;
          if(!player.arrestor_hook) player.arrested = false;
        }
        if(pressed(GLFW_KEY_W) && player.landed) player.wheel_brake = !player.wheel_brake;
        if(pressed(GLFW_KEY_B)) {
          if(down(GLFW_KEY_LEFT_ALT) || down(GLFW_KEY_RIGHT_ALT)) {
            if(player.aircraft != tfx::flight::player_aircraft::raptor && !player.brake_chute_cut_away && player.fixed_speed >= 20) { player.brake_chute = true;scene.actor_event(player_visual,15); }
          } else if(down(GLFW_KEY_LEFT_SHIFT) || down(GLFW_KEY_RIGHT_SHIFT)) {
            if(player.aircraft != tfx::flight::player_aircraft::raptor && player.brake_chute) { player.brake_chute = false;player.brake_chute_cut_away = true;scene.actor_event(player_visual,16); }
          } else {
            auto &condition{player_damage.systems[std::to_underlying(tfx::flight::aircraft_system::air_brake)]};
            if(condition != tfx::flight::system_condition::failed) {
              player.air_brake = !player.air_brake;
              condition = player.air_brake ? tfx::flight::system_condition::active : tfx::flight::system_condition::normal;
            }
          }
        }
      }
      timer_fraction += real_elapsed * tfx::simulation::timer_hz;
      auto const ticks{static_cast<tfx::simulation::timer_counter>(std::floor(timer_fraction))};
      timer_fraction -= ticks;
      counter += ticks;
      auto const step{flight_clock.poll(counter)};
      if(step) {
        auto const stick_action{simple_controls.source == tfx::flight::control_source::joystick ? stick_buttons.advance(stick_mask,preferences.stick_type,step->world_ticks) : tfx::flight::joystick_action::none};
        switch(stick_action) {
          case tfx::flight::joystick_action::fire: store_trigger = true;break;
          case tfx::flight::joystick_action::ground_weapon: select_weapon(tfx::weapons::weapon_role::ground);break;
          case tfx::flight::joystick_action::air_weapon: select_weapon(tfx::weapons::weapon_role::air);break;
          case tfx::flight::joystick_action::cycle_target: cycle_target();break;
          case tfx::flight::joystick_action::front_view: views.press(tfx::cockpit::view_key::front,view_keys);break;
          case tfx::flight::joystick_action::left_view: views.press(tfx::cockpit::view_key::left,view_keys);break;
          case tfx::flight::joystick_action::right_view: views.press(tfx::cockpit::view_key::right,view_keys);break;
          case tfx::flight::joystick_action::rear_view: views.press(tfx::cockpit::view_key::rear,view_keys);break;
          case tfx::flight::joystick_action::none: break;
        }
        // Native 0x86820 updates HUD intensity once per flight input frame.
        // Either held key requests a palette upload, even if both cancel out.
        bool const hud_up{down(GLFW_KEY_Y)}, hud_down{down(GLFW_KEY_U)};
        if(hud_up || hud_down) palette_selection.invalidate_normal();
        int constexpr minimum_hud_green{90}, maximum_hud_green{127};
        hud_green = static_cast<int16_t>(std::clamp(hud_green + (hud_up ? 1 : 0) - (hud_down ? 1 : 0),minimum_hud_green,maximum_hud_green));
        // Keyboard supplies a relative stick input until the full native device adapter is restored.
        if(arcade_mode && !designator_view && !view_keys.shift) {
          pitch_input += (down(GLFW_KEY_UP) - down(GLFW_KEY_DOWN)) * step->world_ticks * 4;
          roll_input += (down(GLFW_KEY_RIGHT) - down(GLFW_KEY_LEFT)) * step->world_ticks * 4;
        }
        bool const steer{!designator_view && !view_keys.shift};
        simple_controls.keys = {
          .up{steer && down(GLFW_KEY_UP)},
          .left{steer && down(GLFW_KEY_LEFT)},
          .down{steer && down(GLFW_KEY_DOWN)},
          .right{steer && down(GLFW_KEY_RIGHT)},
        };
        simple_controls.alt = down(GLFW_KEY_LEFT_ALT) || down(GLFW_KEY_RIGHT_ALT);
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
        if(simple_controls.source == tfx::flight::control_source::mouse && !arcade_mode) mouse_control.advance({controls.roll_delta,controls.pitch_delta});
        advance_world(controls,step->world_ticks,step->physics_seconds,down(GLFW_KEY_SPACE),store_trigger,stick_action == tfx::flight::joystick_action::fire);
        store_trigger = false;
        frame_ticks = step->world_ticks;
        flight_clock.begin({
          .model{preferences.model},
        });
      } else {
        glfwWaitEventsTimeout(.002);
        continue;
      }
    }
    if(paused || result_evaluated) glfwWaitEventsTimeout(.01);
    draw();
    window.present(renderer.output.colourise(*frame_colours));
    if(frame_ticks) finish_world(*frame_ticks);
    if(campaign_flight && result_evaluated) break;
    ++frames;
    ++interval_frames;
    if(now - title_time >= .5) {
      window.title(std::string{inspect ? "TFX C++ — scene inspection — " : "TFX C++ — " + std::string{simple_mode ? "Simple" : arcade_mode ? "Arcade" : preferences.model == simulation::flight_model::realistic ? "Realistic" : "Military-spec"} + " flight — "} + mission_name + " / " + environment.name + " / " + environment.lighting_name + " — " + std::to_string(static_cast<int>(interval_frames / (now - title_time))) + " fps");
      title_time = now;
      interval_frames = 0;
    }
    if(frame_limit && frames >= frame_limit) break;
  }
  glfwSetInputMode(host,GLFW_CURSOR,GLFW_CURSOR_NORMAL);
  return result_evaluated ? flight_result::finished : flight_result::quit;
}

} // namespace tfx::platform
