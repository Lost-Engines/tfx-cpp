#include "aerodynamic_step.h"
#include <stdexcept>
#include <utility>
#include "math/floating_environment.h"

namespace tfx::flight {
namespace {

double constexpr realistic_ground_pitch_gain{.2};

} // anonymous namespace

aerodynamic_tick_events advance_aerodynamic_flight(aerodynamic_flight &state, damage_state &damage, math::random_state &random, aerodynamic_wind_parameters const &wind_parameters, aerodynamic_tick_context const &context) {
  math::floating_environment const environment;
  aerodynamic_tick_events events;
  auto &motion{state.response.motion};
  auto &data{state.data};
  auto &manual{state.manual};
  auto &powerplant{state.powerplant};
  auto &ground{state.ground.ground};
  auto const &aircraft{state.aircraft};
  auto const &geometry{aircraft.surfaces};
  auto const craft{aircraft.stores_and_mounts.stores.aircraft};
  bool const realistic{state.model == aerodynamic_model::realistic};
  state.seconds = context.seconds;

  state.wind.simulation_seconds = data.simulation_seconds;
  if(context.wind_enabled) update_aerodynamic_wind(state.wind,wind_parameters,random,{
    .down_metres{motion.pose.metres_ned.z},
    .terrain_wind_boost{context.terrain_wind_boost},
    .weather_wind_boost{context.weather_wind_boost},
  });
  data.simulation_seconds = state.wind.simulation_seconds;
  update_aerodynamic_airdata(data,motion,{
    .wind_ned{vec3f{state.wind.velocity_ned}},
    .empty_mass_kg{aircraft.empty_mass_kg},
    .fuel_kg{powerplant.fuel},
    .stores_kg{state.stores.mass_kg},
    .seconds{context.seconds},
    .atmosphere{aircraft.atmosphere},
    .surface_celsius{context.surface_celsius},
  });
  state.wind.simulation_seconds = data.simulation_seconds;
  state.coefficients = update_aerodynamic_coefficients(craft,data.mach,state.coefficient_parameters);
  aerodynamic_powerplant_context const engine_context{
    .altitude_km{data.altitude_km},
    .seconds{context.seconds},
    .time_warp{context.time_warp},
  };
  powerplant.engine_condition = {
    damage.condition(aircraft_system::left_engine),
    damage.condition(aircraft_system::right_engine),
  };
  if(consume_aerodynamic_fuel(powerplant,aircraft.powerplant,engine_context)) events.afterburner.push_back(afterburner_change::stopped);
  update_aerodynamic_engine_faults(powerplant,random);
  damage.systems[std::to_underlying(aircraft_system::left_engine)] = powerplant.engine_condition[0];
  damage.systems[std::to_underlying(aircraft_system::right_engine)] = powerplant.engine_condition[1];

  aerodynamic_control_context const control_context{
    .source{context.input.source},
    .keys{context.input.keys},
    .joystick{vec2<int16_t>{context.input.joystick}},
    .mouse{vec2<int16_t>{context.input.mouse}},
    .seconds{context.seconds},
    .metres_per_second{data.metres_per_second},
    .pitch_gain{realistic && ground.landed ? realistic_ground_pitch_gain : state.input_gains.pitch},
    .roll_gain{state.input_gains.roll},
    .rudder_increment{state.input_gains.rudder},
    .joystick_gain{state.input_gains.joystick},
    .elevator_trim{manual.elevator_trim},
    .maximum_autopilot_speed{aircraft.maximum_autopilot_speed},
    .alt{context.input.alt},
    .low_speed_ground_contact{state.response.low_speed_ground_contact},
    .accelerate{context.input.accelerate},
    .decelerate{context.input.decelerate},
  };
  if(update_aerodynamic_controls(manual.controls,powerplant,control_context)) events.afterburner.push_back(afterburner_change::stopped);
  if(realistic && ground.landed && data.metres_per_second < aircraft.stall_metres_per_second) manual.controls.elevator = manual.controls.keyboard_elevator = 0;
  manual.air_brake_condition = damage.condition(aircraft_system::air_brake);
  aerodynamic_manual_context const manual_context{
    .data{data},
    .coefficients{state.coefficients},
    .surfaces{state.surfaces},
    .geometry{geometry},
    .aircraft{craft},
    .source{context.input.source},
    .maximum_g{aircraft.maximum_g},
    .minimum_g{aircraft.minimum_g},
    .cockpit_upward_metres{aircraft.cockpit_upward_metres},
    .engine_pitch_arm{aircraft.powerplant.pitch_thrust_arm},
    .body_down_force{state.forces.body_force.z},
    .body_forward_force{state.forces.body_force.x},
    .accumulated_damage{damage.accumulated},
    .afterburner_stages{aircraft.powerplant.afterburner_stages},
    .military{!realistic},
    .stick_pressure{context.stick_pressure},
    .flaps_condition{damage.condition(aircraft_system::flaps)},
  };
  auto &autopilot{state.autopilot};
  // These original globals are scratch shared with the following ground and
  // response stages; transfer at their call boundaries, not through stale copies.
  autopilot.guidance.ground_speed = state.response.previous_pitch_rate;
  autopilot.guidance.roll_angle = state.ground.roll_angle;
  aerodynamic_guidance_context const guidance_context{
    .law{manual_context},
    .engine{aircraft.powerplant},
    .seconds{context.seconds},
    .roll_moment{state.stores.total_moment_a},
    .pitch_moment{state.stores.total_moment_b},
    .previous_drag{state.surfaces.drag},
    .rudder_effectiveness{aircraft.rudder_effectiveness},
    .followed_aircraft{context.navigation.followed_aircraft.has_value()},
    .time_warp{context.time_warp},
    .recovery{
      .afterburner_stages{aircraft.powerplant.afterburner_stages},
      .available{context.recovery_available},
      .inhibited{context.recovery_inhibited},
      .crashed{motion.collision != 0},
      .ejected{context.ejected},
      .landed{ground.landed},
    },
  };
  auto const controlled{update_aerodynamic_autopilot(autopilot,manual,powerplant,motion,{
    .guidance{guidance_context},
    .navigation{context.navigation},
  })};
  events.afterburner.insert(events.afterburner.end(),controlled.afterburner.begin(),controlled.afterburner.end());
  events.recovery = controlled.recovery;
  state.response.previous_pitch_rate = autopilot.guidance.ground_speed;
  state.ground.roll_angle = autopilot.guidance.roll_angle;
  damage.systems[std::to_underlying(aircraft_system::air_brake)] = manual.air_brake_condition;
  if(realistic) update_aerodynamic_commands(state.commands,manual,powerplant,{
    .data{data},
    .coefficients{state.coefficients},
    .geometry{geometry},
    .engine_roll_arm{aircraft.powerplant.roll_thrust_arm},
    .engine_pitch_arm{aircraft.powerplant.pitch_thrust_arm},
    .body_forward_force{state.forces.body_force.x},
    .body_down_force{state.forces.body_force.z},
    .seconds{context.seconds},
    .stick_pressure{context.stick_pressure},
  });
  update_aerodynamic_surfaces(state.surfaces,geometry,{
    .aircraft{craft},
    .coefficients{state.coefficients},
    .angle_of_attack{data.angle_of_attack},
    .metres_per_second{data.metres_per_second},
    .density{data.atmosphere.density},
    .dynamic_pressure{data.dynamic_pressure},
    .flap_fraction{manual.flap_fraction},
    .gear_fraction{state.gear_fraction},
    .air_brake_fraction{manual.air_brake_fraction},
    .elevator{manual.controls.elevator},
    .aileron{manual.controls.aileron},
    .sideslip{state.response.sideslip_radians},
    .pitch_rate{motion.angular_rate.y},
    .roll_rate{motion.angular_rate.x},
    .chute_deployed{state.chute_deployed},
    .calculate_moments{!realistic},
    .flaps_condition{damage.condition(aircraft_system::flaps)},
  });
  update_aerodynamic_thrust(powerplant,aircraft.powerplant,engine_context);
  aerodynamic_ground_context const ground_context{
    .contact{
      .basis{data.basis},
      .ground_elevation_steps{context.ground_elevation_steps},
      .body_downward_q15{math::signed_word(static_cast<uint16_t>(motion.pose.frame.down.z))},
      .total_mass_kg{data.mass_kg},
      .terrain_present{context.terrain_present},
      .gear_damage_enabled{context.gear_damage_enabled},
      .low_speed_ground_contact{state.response.low_speed_ground_contact},
      .precipitation{context.precipitation},
      .rough_surface{context.rough_surface},
      .wheel_brakes{context.wheel_brakes},
    },
    .previous_ned_force{vec3d{state.forces.ned_force}},
    .engine_factor{vec2d{powerplant.engine_factor}},
    .gear_fraction{state.gear_fraction},
    .metres_per_second{data.metres_per_second},
    .seconds{context.seconds},
    .throttle{powerplant.throttle},
    .carrier_surface{context.carrier_surface},
    .arrestor_hook_down{state.arrestor_hook_down},
  };
  // Native 0x143c8 is shared ground scratch and retained pitch-rate storage.
  ground.cable_speed = state.response.previous_pitch_rate;
  if(realistic) {
    state.ground.commanded_roll_rate = state.commands.roll_rate;
    state.ground.commanded_angle_of_attack = state.commands.angle_of_attack;
    events.ground = update_aerodynamic_realistic_ground(state.ground,motion,manual.controls,damage,random,aircraft.ground,{
      .ground{ground_context},
      .stall_metres_per_second{aircraft.stall_metres_per_second},
      .angle_of_attack{data.angle_of_attack},
      .lift{state.surfaces.lift},
    });
    state.commands.roll_rate = state.ground.commanded_roll_rate;
    state.commands.angle_of_attack = state.ground.commanded_angle_of_attack;
  } else events.ground = update_aerodynamic_ground(ground,motion,damage,random,aircraft.ground,ground_context);
  state.response.previous_pitch_rate = ground.cable_speed;

  aerodynamic_inertia const inertia{
    .mass_kg{data.mass_kg},
    .roll_moment{state.stores.total_moment_a},
    .pitch_moment{state.stores.total_moment_b},
    .fuel_kg{powerplant.fuel},
  };
  state.forces = update_aerodynamic_forces(motion,{
    .basis{data.basis},
    .loads{
      .aerodynamic_force{vec3d{state.surfaces.force}},
      .engine_force{vec3d{powerplant.engine_force}},
      .ground_force{vec3d{ground.contact.force}},
      .aerodynamic_moment{vec3d{state.surfaces.moment}},
      .engine_moment{vec3d{powerplant.engine_moment}},
      .ground_moment{vec3d{ground.contact.moment}},
    },
    .inertia{inertia},
    .cockpit_upward_metres{aircraft.cockpit_upward_metres},
    .refuelling_connected{context.refuelling_phase == 3},
    .fully_arrested{ground.arrestor == aerodynamic_arrestor_phase::stopped},
  });
  state.response.g_load = state.forces.g_load;
  update_aerodynamic_response(state.response,{
    .basis{data.basis},
    .inertia{inertia},
    .parameters{
      .wing_area{geometry.wing_area},
      .wing_span{geometry.wing_span},
      .mean_chord{geometry.mean_chord},
      .maximum_aileron_radians{geometry.maximum_aileron_angle},
      .rudder_effectiveness{aircraft.rudder_effectiveness},
      .roll_damping{state.coefficients.roll_damping},
      .pitch_damping{state.coefficients.pitch_damping},
      .pitch_stability{state.coefficients.pitch_stability},
      .zero_pitch_moment{geometry.zero_pitch_moment},
      .roll_thrust_arm{aircraft.powerplant.roll_thrust_arm},
      .pitch_thrust_arm{aircraft.powerplant.pitch_thrust_arm},
      .maximum_elevator_angle{geometry.maximum_elevator_angle},
    },
    .seconds{context.seconds},
    .metres_per_second{data.metres_per_second},
    .density{data.atmosphere.density},
    .stall_metres_per_second{aircraft.stall_metres_per_second},
    .rudder{manual.controls.rudder},
    .aileron{manual.controls.aileron},
    .elevator{manual.controls.elevator},
    .roll_control_gradient{state.coefficients.aileron_effectiveness},
    .pitch_control_gradient{state.coefficients.elevator_moment},
    .engine_thrust{powerplant.thrust},
    .thrust_moment_scale{manual.thrust_vector_fraction},
    .angle_of_attack{data.angle_of_attack},
    .pitch_rate_bias{manual.pitch_rate_bias},
    .ground_vertical_force{ground.contact.force.z},
    .time_warp{context.time_warp},
    .landed{ground.landed},
    .autopilot{manual.controls.autopilot.enabled},
    .rudder_inhibited{ground.ground_steering},
    .realistic{realistic},
    .stick_pressure{context.stick_pressure},
  });
  ground.cable_speed = state.response.previous_pitch_rate;
  advance_aerodynamic_motion(motion,{
    .seconds{context.seconds},
    .time_warp{context.time_warp},
    .landed{ground.landed},
    .crashing{context.crashing},
    .simplified_rotation{realistic},
    .roll_rate_inhibited{context.refuelling_phase != 0},
    .commanded_roll_rate{state.commands.roll_rate},
    .commanded_angle_of_attack{state.commands.angle_of_attack},
    .angle_of_attack{data.angle_of_attack},
  });
  state.view = update_aerodynamic_view(motion.pose,craft,aircraft.viewpoint);
  motion.integer_world_y = state.view.integer_position.y;
  if(realistic && ground.contact.force.x != 0) motion.velocity_ned.z = 0;
  autopilot.guidance.ground_speed = state.response.previous_pitch_rate;
  autopilot.guidance.roll_angle = state.ground.roll_angle;
  return events;
}

} // namespace tfx::flight
