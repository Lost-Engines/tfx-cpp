#pragma once

#include <variant>
#include "missions/initialisation.h"
#include "missions/rules.h"
#include "missions/timeline.h"

namespace tfx::missions {

enum class session_outcome : int32_t { normal, aircraft_lost, violated_orders, ejected, critical_loss = 99 };
enum class session_status : int32_t { normal, critical_loss, violated_orders, missing, aircraft_lost };
enum class notice_kind { target_destroyed, completion, protection_failed, timer_expired };
struct progress_notice {
  notice_kind kind;
  unsigned int target{0};
};
struct mission_completed_event {};
using progress_event = std::variant<progress_notice,mission_completed_event>;

struct loss_effects {
  std::optional<unsigned int> acknowledgement_sample{};
  bool friendly_target{false};
};
struct player_loss_context {
  bool fatal;
  bool collision;
  simulation::timer_ticks elapsed;
  bool invulnerable{false};
  int32_t height{0}; // World-integer down coordinate; airborne values are negative.
};
struct player_loss_effects {
  bool first_loss{false};
  bool explosion{false};
  bool mayday{false};
};
struct progress_context {
  mission_tick mission_time;
  simulation::timer_ticks elapsed;
  std::span<target_life const> targets;
  bool landed{false};
  int32_t speed{0};
  bool arcade{false};
};
class progress {
private:
  setup const &initialisation;
  std::vector<uint8_t> reported;
  void set_termination(bool arcade);

public:
  result_state results;
  int32_t return_score{0};
  int16_t target_cursor{0};
  int16_t violations{0};
  int16_t exit_ticks{0};
  int32_t remaining_timer{-1};
  bool resolved{false};
  bool ended{false};
  bool critical_loss{false};
  bool player_ejected{false};
  bool impact_started{false};
  int16_t death_ticks{0};
  session_outcome outcome{session_outcome::normal};
  session_status status{session_status::normal};
  explicit progress(setup const &source);
  void reset();
  player_loss_effects observe_player_loss(player_loss_context const &context);
  loss_effects record_air_loss(bool enemy_pool, int16_t type, bool player_owned, bool authorised, math::random_state &random);
  loss_effects record_surface_loss(bool hostile, int16_t type);
  std::vector<progress_event> begin_frame(progress_context const &context);
  bool finish_frame(simulation::timer_ticks elapsed);
};

} // namespace tfx::missions
