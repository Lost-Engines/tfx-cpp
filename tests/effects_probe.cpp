#include <fstream>
#include <iostream>
#include <stdexcept>
#include <utility>
#include <vector>
#include "world/effects.h"

int main(int const argc, char const *const argv[]) try {
  std::ifstream fixture;
  if(argc == 2) fixture.open(argv[1]);
  if(argc > 2 || (argc == 2 && !fixture)) throw std::runtime_error{"expected [FILE]"};
  auto &input{argc == 2 ? fixture : std::cin};
  tfx::world::effect_pool effects;
  char command;
  unsigned int cases{0};
  while(input >> command) {
    std::vector<int64_t> events;
    if(command == 'R') effects.reset();
    else if(command == 'S') {
      vec3<int32_t> position;
      unsigned int kind;
      if(!(input >> position.x >> position.y >> position.z >> kind)) throw std::runtime_error{"incomplete effect spawn"};
      if(kind == std::to_underlying(tfx::world::effect_kind::cannon_hit)) events = {0,1,14};
      auto const slot{effects.spawn(position,static_cast<tfx::world::effect_kind>(kind))};
      events.insert(events.end(),{1,slot,kind});
    } else throw std::runtime_error{"unknown effect probe command"};
    std::vector<int64_t> values;
    for(auto const slot : effects.active_slots()) {
      auto const &effect{effects.record(slot)};
      values.insert(values.end(),{slot,std::to_underlying(effect.kind),effect.position.x,effect.position.y,effect.position.z});
    }
    values.insert(values.begin(),static_cast<int64_t>(values.size() / 5));
    values.push_back(static_cast<int64_t>(events.size()));
    values.insert(values.end(),events.begin(),events.end());
    uint64_t digest{14695981039346656037ULL};
    for(auto const value : values) for(unsigned int shift{0}; shift != 32; shift += 8) digest = (digest ^ ((static_cast<uint32_t>(value) >> shift) & 255)) * 1099511628211ULL;
    if(argc == 2) { uint64_t expected;if(!(input >> expected) || expected != digest) throw std::runtime_error{"effect pool mismatch at case " + std::to_string(cases)}; }
    else std::cout << digest << '\n';
    ++cases;
  }
  return cases ? 0 : 1;
} catch(std::exception const &error) { std::cerr << error.what() << '\n';return 1; }
