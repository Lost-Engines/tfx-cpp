#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <ranges>
#include "resources/executable_tables.h"
#include "weapons/runtime.h"

int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"projectile_runtime_probe DATA_DIRECTORY"};
  tfx::resources::executable_tables const tables{std::filesystem::path{argv[1]} / "TFX.DAT"};
  unsigned int frames{0},elapsed{0},dispenser{0},capacity{0};
  while(std::cin >> frames >> elapsed >> dispenser >> capacity) {
    std::vector<int32_t> events;
    vec3<int32_t> designation{2000000,-200000,3000000};
    tfx::weapons::runtime state{tables.weapons,{
      .mount_state{[] { return tfx::weapons::launch_mount{.angles{0,12000,0},.selected{4}}; }},
      .actor_position{[](tfx::weapons::actor_identity) { return vec3<int32_t>{1000000,-300000,1000000}; }},
      .designation_position{[&] { return vec3<int32_t>{designation}; }},
      .motion_inputs{[](tfx::weapons::active_projectile const&,uint16_t const ticks) {
        return tfx::weapons::motion_context{
          .elapsed{ticks},
          .target{0,0,0},
          .launch_anchor{1001000,-300500,1002000},
          .player_angles{0,12000,0},
          .player_speed{400},
        };
      }},
      .reset_visual{[&](unsigned int const weapon, bool const secondary) { events.insert(events.end(),{0,static_cast<int32_t>(weapon),secondary}); }},
      .launched{[&](tfx::weapons::active_projectile const &shot) { events.insert(events.end(),{1,static_cast<int32_t>(shot.id)}); }},
      .target_cleared{[&](tfx::weapons::active_projectile const &shot) { events.insert(events.end(),{2,static_cast<int32_t>(shot.id)}); }},
      .contacts{[&](tfx::weapons::active_projectile &shot,uint16_t const ticks) { events.insert(events.end(),{3,static_cast<int32_t>(shot.id),ticks}); }},
    },capacity};
    tfx::math::random_state random;
    for(unsigned int index{0}; index != (dispenser == 1 ? 3u : 27u); ++index) state.launch({
      .weapon{dispenser == 1 ? index == 0 ? 15u : index == 1 ? 16u : 0u : index},
      .position{1000000,-300000,1000000},
      .angles{0,12000,0},
      .speed{400},
      .owner{
        .pool{tfx::weapons::actor_pool::aircraft},
      },
      .target{
        .position{2000000,-200000,3000000},
        .actor{dispenser >= 2 && dispenser <= 3 ? std::optional{tfx::weapons::actor_identity{.pool{tfx::weapons::actor_pool::aircraft}}} : std::nullopt},
        .untargeted{dispenser == 4},
        .designated{dispenser == 5},
      },
    });
    for(unsigned int frame{0}; frame != frames; ++frame) {
      events.clear();
      if(dispenser == 5) designation = vec3<int32_t>{2000000 + static_cast<int32_t>(frame) * 10000,-200000,3000000 - static_cast<int32_t>(frame) * 7000};
      if(dispenser >= 2 && dispenser <= 3 && frame == 2) state.countermeasure({.pool{tfx::weapons::actor_pool::aircraft}},{1000000,-300000,1000000},dispenser == 2,64,random);
      state.advance(static_cast<uint16_t>(elapsed),random,false);
      uint64_t digest{14695981039346656037ULL};
      auto const word{[&](auto const value) {
        for(unsigned int shift{0}; shift != 32; shift += 8) digest = (digest ^ ((static_cast<uint32_t>(value) >> shift) & 255)) * 1099511628211ULL;
      }};
      word(state.projectiles().size());
      for(auto const &[id,shot] : state.projectiles() | std::views::reverse) {
        auto const &body{shot->state};
        word(id); word(body.weapon); word(body.next_stage); word(std::to_underlying(body.motion)); word(body.ticks);
        for(auto const value : {body.position.x,body.position.y,body.position.z,body.previous.x,body.previous.y,body.previous.z}) word(value);
        for(auto const value : {body.angles.x,body.angles.y,body.angles.z}) word(value);
        word(body.speed); word(body.fall_speed); word(body.acceleration); word(body.range); word(body.secondary); word(shot->spent); word(shot->mount);
      }
      word(events.size());
      for(auto const value : events) word(value);
      std::cout << digest << '\n';
    }
  }
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << std::endl;
  return EXIT_FAILURE;
}
