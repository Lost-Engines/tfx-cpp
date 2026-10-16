#include "framebuffer.h"
#include <algorithm>
#include <fstream>
#include <stdexcept>

namespace tfx::render {

std::vector<rgba_pixel> framebuffer::colourise(palette const &colours) const {
  /// Keep palette indices through software drawing; RGB conversion happens only at presentation
  std::vector<rgba_pixel> result;
  result.reserve(pixels.size());
  for(auto const index : pixels) {
    auto const &colour{colours[index]};
    result.emplace_back(colour.r, colour.g, colour.b, 255);
  }
  return result;
}

void framebuffer::screenshot(std::filesystem::path const &path, palette const &colours) const {
  std::ofstream stream{path, std::ios::binary};
  stream.exceptions(std::ios::failbit | std::ios::badbit);
  stream << "P6\n" << screen_width << ' ' << screen_height << "\n255\n";
  for(auto const index : pixels) {
    auto const &colour{colours[index]};
    stream.write(reinterpret_cast<char const*>(colour.data()), 3);
  }
}

palette decode_palette(std::span<uint8_t const> const source) {
  /// Expand VGA's six-bit DAC values without blending between palette entries
  if(source.size() != 256 * 3) throw std::runtime_error{"palette does not contain 256 RGB triples"};
  palette result;
  for(unsigned int i{0}; i != result.size(); ++i) {
    for(unsigned int channel{0}; channel != 3; ++channel) {
      auto const value{source[i * 3 + channel]};
      if(value > 63) throw std::runtime_error{"palette component exceeds the VGA DAC range"};
      result[i][channel] = static_cast<uint8_t>((value * 255 + 31) / 63);
    }
  }
  return result;
}

palette expand_dac_palette(dac_palette const &source) {
  // VGA's six-bit DAC ignores the upper two bits. Live HUDCOL brightness
  // deliberately stores 90..127; authored palette files remain strictly checked.
  dac_palette visible;
  std::ranges::transform(source,visible.begin(),[](uint8_t const value) { return static_cast<uint8_t>(value & 63); });
  return decode_palette(visible);
}

} // namespace tfx::render
