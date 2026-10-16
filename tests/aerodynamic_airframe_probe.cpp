#include <bit>
#include <fstream>
#include <iostream>
#include <string_view>
#include "flight/aerodynamic_airframes.h"

namespace {

void profile(tfx::flight::aerodynamic_airframe const &frame) {
  auto const number{[](double const value) { std::cout << std::bit_cast<uint64_t>(value) << ' '; }};
  auto const &load{frame.stores_and_mounts};
  for(auto const value : {load.stores.moment_a,load.stores.moment_b,load.stores.fuel_capacity}) number(value);
  for(auto const &position : load.mounts) for(auto const value : position) number(value);
  auto const &p{frame.surfaces};
  for(auto const value : {p.wing_area,p.wing_span,p.mean_chord,p.flap_lift_gradient,p.maximum_flap_angle,p.flap_limit_gradient,p.maximum_lift,p.automatic_flap_gradient,p.maximum_automatic_flap_angle,p.zero_lift,p.critical_angle,p.induced_drag,p.air_brake_drag,p.gear_drag,p.elevator_drag,p.chute_area,p.zero_pitch_moment,p.chute_pitch_arm,p.air_brake_moment_arm.x,p.air_brake_moment_arm.y,p.maximum_aileron_angle,p.maximum_elevator_angle}) number(value);
  auto const c{frame.initial_coefficients()};
  for(auto const value : {c.base_drag,c.critical_mach,c.full_wave_drag_mach,c.wave_drag_increment,c.wing_area,c.additional_lifting_area,c.pitch_stability_base,c.pitch_stability_correction,c.pitch_damping_mach_gradient,c.pitch_damping_base,c.elevator_moment_gradient,c.elevator_lift_gradient,c.roll_damping_gradient,c.aileron_gradient}) number(value);
  auto const &engine{frame.powerplant};
  for(auto const value : {engine.dry_thrust,engine.afterburner_thrust,engine.ceiling_km,engine.dry_fuel_coefficient,engine.afterburner_fuel_coefficient,engine.roll_thrust_arm,engine.pitch_thrust_arm,frame.viewpoint.forward,frame.viewpoint.upward,frame.empty_mass_kg,frame.maximum_g,frame.minimum_g,frame.cockpit_upward_metres,frame.stall_metres_per_second,frame.low_speed_reference,frame.cruise_mach}) number(value);
  std::cout << static_cast<unsigned int>(engine.afterburner_stages) << '\n';
}

} // anonymous namespace

int main(int const argc, char const *const argv[]) try {
  if(argc < 2) throw std::runtime_error{"expected TFX.DAT or --calibration [FILE]"};
  if(std::string_view{argv[1]} != "--calibration") {
    if(argc != 2) throw std::runtime_error{"expected TFX.DAT"};
    for(auto const &frame : tfx::flight::load_aerodynamic_airframes(tfx::resources::read_file(argv[1]))) profile(frame);
    return 0;
  }
  std::ifstream fixture;
  if(argc == 3) fixture.open(argv[2]);
  if(argc > 3 || (argc == 3 && !fixture)) throw std::runtime_error{"cannot open aerodynamic calibration fixtures"};
  auto &input{argc == 3 ? fixture : std::cin};
  unsigned int cases{0};
  uint64_t first;
  while(input >> first) {
    tfx::flight::aerodynamic_airframe frame;
    frame.coefficient_base.pitch_stability_base = std::bit_cast<double>(first);
    std::array<double *,9> const fields{&frame.coefficient_base.pitch_damping_base,&frame.coefficient_base.elevator_moment_gradient,&frame.surfaces.flap_limit_gradient,&frame.surfaces.maximum_flap_angle,&frame.surfaces.maximum_lift,&frame.surfaces.automatic_flap_gradient,&frame.surfaces.maximum_automatic_flap_angle,&frame.surfaces.maximum_elevator_angle,&frame.stores_and_mounts.stores.moment_b};
    for(auto *field : fields) { uint64_t bits; input >> bits; *field = std::bit_cast<double>(bits); }
    uint64_t previous; input >> previous;
    auto const calibrated{frame.initial_coefficients(std::bit_cast<double>(previous))};
    for(auto const value : {calibrated.pitch_stability_correction,calibrated.pitch_damping_mach_gradient}) {
      auto const actual{std::bit_cast<uint64_t>(value)};
      if(argc == 3) {
        uint64_t expected;
        if(!(input >> expected) || actual != expected) throw std::runtime_error{"native aerodynamic calibration differs"};
      } else std::cout << actual << ' ';
    }
    if(argc == 2) std::cout << '\n';
    ++cases;
  }
  if(!cases) throw std::runtime_error{"no aerodynamic calibration cases"};
  if(argc == 3) std::cout << cases << " native aerodynamic calibration fixtures agree\n";
  return 0;
} catch(std::exception const &error) { std::cerr << error.what() << '\n'; return 1; }
