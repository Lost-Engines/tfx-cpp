#pragma once

#include "presentation/program.h"

namespace tfx::presentation {

class runtime {
private:
  program const &source;
  variables &state;
  std::optional<location> cursor;
  std::vector<std::optional<location>> callers;
  std::optional<location> successor() const;

public:
  explicit runtime(program const &source, variables &state, location entry = {0,0});
  std::optional<location> position() const;
  unsigned int call_depth() const;
  statement const *current() const;
  // Execute numeric control flow until an audiovisual/menu/session action needs its host.
  statement const *run();
  void complete();
};

} // namespace tfx::presentation
