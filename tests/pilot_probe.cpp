#include <chrono>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include "presentation/frontend.h"

namespace {
void require(bool const condition, char const *const message) {
  if(!condition) throw std::runtime_error{message};
}
struct scratch_directory {
  std::filesystem::path path{std::filesystem::temp_directory_path() / ("tfx-pilot-check-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()))};
  scratch_directory() {
    if(!std::filesystem::create_directory(path)) throw std::runtime_error{"cannot create private pilot-test directory"};
  }
  ~scratch_directory() {
    std::error_code ignored;
    std::filesystem::remove_all(path,ignored);
  }
};
} // anonymous namespace
int main(int const argc, char const *const argv[]) try {
  if(argc != 2) throw std::runtime_error{"pilot_probe DATA_DIRECTORY"};
  auto const archive{tfx::resources::find_game_archive(argv[1])};
  tfx::resources::archive const game{archive};
  tfx::resources::executable_tables const tables{archive.parent_path() / "TFX.DAT"};
  tfx::presentation::program const schema{game.read("tfx.par")};
  scratch_directory const scratch;
  tfx::presentation::pilot_store store{scratch.path};
  tfx::presentation::frontend first{game,tables,scratch.path,"english",true};
  tfx::presentation::scene_input input;
  uint32_t ticks{0};
  auto const step{[&](tfx::presentation::frontend &frontend, unsigned int const count) {
    for(unsigned int index{0}; index != count; ++index) {
      auto const *action{frontend.advance({ticks++,ticks * 3},input)};
      require(!action,"front-end unexpectedly reached an external host action");
    }
  }};
  step(first,50);
  first.press(0x1c,false); // Create, then accept each original default name.
  first.press(0x1c,false);
  first.press(1,false);
  first.press(0x1c,true);
  require(std::get<std::string>(first.values().at("firstname")) == "DIRK","first-name default differs");
  require(std::get<std::string>(first.values().at("pilotname")) == "LOOSE CANNON","surname Escape default differs");
  require(std::get<std::string>(first.values().at("callsign")) == "INFERNO","callsign default differs");
  require(std::get<uint32_t>(first.values().at("rank")) == 1,"Control qualification differs");
  first.press(0x1c,false); // Empty slot zero.
  step(first,100);
  auto saved{store.read(0,false,schema)};
  require(saved.resume && saved.resume->function == 0 && saved.resume->statement == 5,"enrolment saved the wrong native resume statement");
  require(saved.values == first.values(),"new pilot did not persist its complete state");

  tfx::presentation::frontend loaded{game,tables,scratch.path,"english",true};
  step(loaded,50);
  loaded.press(0x50,false);loaded.press(0x1c,false);loaded.press(0x1c,false);
  step(loaded,100);
  require(loaded.values() == first.values(),"loading selected pilot did not restore its complete campaign variables");
  // The archive's authored FWS menu choice leads through its briefings to mission 501.
  input.mouse_buttons = 1;
  loaded.advance({ticks++,ticks * 3},input,vec2<int16_t>{120,76});
  input.mouse_buttons = 0;
  tfx::presentation::statement const *launch{nullptr};
  for(unsigned int index{0}; index != 20000 && !launch; ++index) {
    input.key = tfx::presentation::scene_key::escape;
    launch = loaded.advance({ticks++,ticks * 3},input);
  }
  require(launch && launch->kind == tfx::presentation::node_kind::launch,"FWS did not yield a flight launch");
  require(std::get<tfx::presentation::host_action>(launch->data).resource == "%mission" && std::get<uint32_t>(loaded.values().at("mission")) == 501,"FWS selected the wrong first engagement");
  // A supplied flight result tests the parser host boundary, independently of flight/combat proof.
  loaded.values()["score"] = uint32_t{123};
  loaded.values()["miss_val"] = uint32_t{1};
  loaded.values()["outcome"] = uint32_t{0};
  loaded.complete();launch = nullptr;
  for(unsigned int index{0}; index != 20000 && !launch; ++index) {
    input.key = tfx::presentation::scene_key::escape;
    launch = loaded.advance({ticks++,ticks * 3},input);
  }
  require(launch && std::get<uint32_t>(loaded.values().at("mission")) == 502,"training did not continue to the second engagement");
  require(std::get<uint32_t>(loaded.values().at("score")) == 10123,"training overwrote the pilot's accumulated score");

  // Existing lower-case DOS files and the original completed-training marker remain interoperable.
  std::filesystem::rename(scratch.path / "TFXSAV.0",scratch.path / "tfxsav.0");
  store.write(0,false,schema,saved);
  require(!std::filesystem::exists(scratch.path / "TFXSAV.0"),"save created a duplicate file differing only in case");
  saved.values["status"] = uint32_t{1};
  store.write(0,false,schema,saved);
  tfx::presentation::frontend retired{game,tables,scratch.path,"english",true};
  step(retired,50);
  retired.press(0x50,false);retired.press(0x1c,false);retired.press(0x1c,false);
  retired.press(0x15,false); // Delete means mark empty in the chooser, not remove the on-disk save.
  require(std::filesystem::exists(scratch.path / "tfxsav.0"),"inactive pilot confirmation prematurely removed the original file");
  retired.press(0x1c,false);retired.press(0x1c,false);retired.press(0x1c,false);retired.press(0x1c,false);
  step(retired,100);
  require(std::get<uint32_t>(store.read(0,false,schema).values.at("status")) == 0,"empty/inactive slot replacement did not save a new active pilot");
  require(!store.trained(),"fresh test pilot was already trained");
  store.complete_training();require(store.trained(),"completed-training marker did not roundtrip");
  tfx::presentation::frontend qualified{game,tables,scratch.path,"english",true};
  step(qualified,50);
  qualified.press(0x1c,false);qualified.press(0x1c,false);qualified.press(0x1c,false);qualified.press(0x1c,false);
  require(std::get<uint32_t>(qualified.values().at("rank")) == 1,"completed training did not qualify a new pilot");
  std::cout << "Pilot creation, Control qualification, DOS slot storage/load/replacement, native resume, training entry/continuation and qualification marker passed in a private directory\n";
  return EXIT_SUCCESS;
} catch(std::exception const &error) {
  std::cerr << "ERROR: " << error.what() << '\n';
  return EXIT_FAILURE;
}
