#pragma once

#include <optional>
#include <string>
#include "configuration/settings.h"

namespace tfx::configuration {

// Native 0xa6808 updates only these four preferences, retaining other lines.
// Missing/empty/oversized input has no output. Unlike the original fixed stack
// buffer, an expanded file cannot overflow or exceed the reader's size limit.
std::optional<std::string> update_preferences(std::string_view original, settings const &state);
bool save_preferences(std::filesystem::path const &directory, settings const &state);

} // namespace tfx::configuration
