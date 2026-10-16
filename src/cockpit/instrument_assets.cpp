#include "instrument_assets.h"
#include <algorithm>
#include <stdexcept>

namespace tfx::cockpit {

instrument_assets::instrument_assets(std::span<uint8_t const> const executable) {
  resources::binary_view const source{executable};
  unsigned int constexpr data{973476};
  auto const string{[&](unsigned int const address) {
    std::string result;
    for(unsigned int index{0}; index != 128; ++index) {
      auto const byte{source.byte(data + address + index)};
      if(!byte) return result;
      result.push_back(static_cast<char>(byte));
    }
    throw std::runtime_error{"unterminated original instrument string"};
  }};
  auto const resource{[&](unsigned int const address) {
    auto name{string(address)};
    std::ranges::replace(name,'\\','/');
    if(name.starts_with('/')) name.erase(0,1);
    return name;
  }};
  auto const real{[&](unsigned int const address) {
    return std::bit_cast<double>(static_cast<uint64_t>(source.le32(data + address)) | (static_cast<uint64_t>(source.le32(data + address + 4)) << 32));
  }};
  for(unsigned int index{0}; index != character_map.size(); ++index) character_map[index] = source.byte(data + 0x7688 + index);
  font_bank = resource(0x166c);
  heading_bank = resource(0x1590);
  pitch_bank = resource(0x15a0);
  for(unsigned int index{0}; index != pitch_marks.size(); ++index) {
    auto &mark{pitch_marks[index]};
    mark.label = source.signed_le16(data + 0x7170 + index * 4);
    mark.dashed = source.le16(data + 0x7172 + index * 4) != 0;
    for(unsigned int vertex{0}; vertex != mark.vertices.size(); ++vertex) mark.vertices[vertex] = {
      source.signed_le16(data + 0x721c + index * 24 + vertex * 4),
      source.signed_le16(data + 0x721e + index * 24 + vertex * 4),
    };
  }
  in_range_label = string(0x179c);
  brake_messages = {string(0x171c),string(0x1728),string(0x1734)};
  hud_number_formats = {string(0x1768),string(0x1770),string(0x1778),string(0x1780),string(0x1784)};
  hud_altitude_scale = std::bit_cast<float>(source.le32(data + 0x178b));
  hud_throttle_scale = std::bit_cast<float>(source.le32(data + 0x178f));
  unsigned_clock_formats = {string(0x17e4),string(0x17ec)};
  signed_clock_formats = {string(0x17f0),string(0x17f8)};
  fuel_format = string(0x17fc);
  critical_fuel = real(0x1803);
  low_fuel = real(0x180b);
  throttle_formats = {string(0x181c),string(0x1818),string(0x1814)};
  throttle_percent = std::bit_cast<float>(source.le32(data + 0x1821));
  ecm_label = string(0x1828);
  stealth_label = string(0x182c);
  decoy_formats = {string(0x1838),string(0x1834)};
  warning_banks = {resource(0x15b4),resource(0x15c8)};
  for(unsigned int index{0}; index != condition_frames.size(); ++index) condition_frames[index] = source.byte(data + 0x7626 + index);
  auxiliary_banks = {resource(0x16a4),resource(0x1658),resource(0x1648)};
  engine_lamp_cache = {source.byte(data + 0x7157),source.byte(data + 0x7156)};
  for(unsigned int index{0}; index != afterburner_pips.size(); ++index) afterburner_pips[index] = {source.signed_le16(data + 0x6c44 + index * 4),source.signed_le16(data + 0x6c46 + index * 4)};
  display_bank = resource(0x1694);
  controls_bank = resource(0x1620);
  autopilot_bank = resource(0x1680);
  autopilot_number_format = string(0x16dc);
  autopilot_label = string(0x1bf8);
  autopilot_mode_labels = {string(0x1c00),string(0x1c20),string(0x1c2c),string(0x1c3c),string(0x1c4c)};
  configuration_labels = {string(0x1c54),string(0x1c5c),"",string(0x1c64),string(0x1c6c)};
  autopilot_height_speed_format = string(0x1c10);
  autopilot_speed_format = string(0x1c34);
  surface_scale = real(0x1c73);
  raptor_degrees = real(0x1c7b);
  raptor_radians = real(0x579c);
  raptor_pointer_scale = real(0x1c83);
  autopilot_speed_scale = real(0x1c8b);
  autopilot_height_scale = real(0x1c93);
  radar_bank = resource(0x1610);
  radar_format = string(0x1884);
  for(unsigned int index{0}; index != horizontal_scales.size(); ++index) horizontal_scales[index] = {
    .label{source.signed_le16(data + 0x7d80 + index * 2)},
    .world_per_pixel{source.signed_le16(data + 0x7d88 + index * 2)},
  };
  for(unsigned int index{0}; index != bvr_scales.size(); ++index) bvr_scales[index] = {
    .label{source.signed_le16(data + 0x7d90 + index * 2)},
    .world_per_pixel{source.signed_le16(data + 0x7d96 + index * 2)},
  };
  for(unsigned int index{0}; index != bvr_envelope.size(); ++index) bvr_envelope[index] = {source.signed_le16(data + 0x76d2 + index * 4),source.signed_le16(data + 0x76d4 + index * 4)};
  for(unsigned int index{0}; index != display_origins.size(); ++index) display_origins[index] = {source.signed_le16(data + 0x7c98 + index * 8),source.signed_le16(data + 0x7c9a + index * 8)};
  for(unsigned int index{0}; index != display_sizes.size(); ++index) display_sizes[index] = {source.signed_le16(data + 0x7c9c + index * 8),source.signed_le16(data + 0x7c9e + index * 8)};
  camera_blink = source.signed_le16(data + 0x7dc4);
  camera_orbit_angles = {source.le16(data + 0x7dc6),source.le16(data + 0x7dc8),source.le16(data + 0x7dca)};
  camera_orbit_step = source.signed_le16(data + 0x7dcc);
  camera_height_bounds = {std::bit_cast<int32_t>(source.le32(data + 0xac58)),std::bit_cast<int32_t>(source.le32(data + 0xac5c))};
  ground_range_format = string(0x1be8);
  std::array<unsigned int,11> constexpr bitmap_fields{0x7b84,0x7b8c,0x7b93,0x7b9a,0x7ba1,0x7ba9,0x7bb1,0x7bb7,0x7bcc,0x7d9c,0x7db0};
  for(unsigned int index{0}; index != masks.size(); ++index) {
    auto const at{data + bitmap_fields[index]};
    unsigned int const size{2u + ((source.byte(at) + 7u) / 8u) * source.byte(at + 1)};
    masks[index] = resources::decode_monochrome(source.slice(at,size));
  }
  for(unsigned int plane{0}; plane != store_order.size(); ++plane) for(unsigned int slot{0}; slot != store_order[plane].size(); ++slot) {
    store_order[plane][slot] = source.byte(data + 0x7be1 + plane * 10 + slot);
    store_positions[plane][slot] = {source.signed_le16(data + 0x7c00 + plane * 40 + slot * 4),source.signed_le16(data + 0x7c02 + plane * 40 + slot * 4)};
  }
  for(unsigned int index{0}; index != system_positions.size(); ++index) {
    system_positions[index] = {source.signed_le16(data + 0x7cb0 + index * 4),source.signed_le16(data + 0x7cb2 + index * 4)};
    auto const at{data + 0x7d10 + index * 8};
    system_boxes[index] = {{
      {source.signed_le16(at),source.signed_le16(at + 2)},
      {source.signed_le16(at + 4),source.signed_le16(at + 6)},
    }};
    system_labels[index] = string(source.le32(data + 0x7ce0 + index * 4));
  }
  for(unsigned int index{0}; index != fuel_cells.size(); ++index) {
    auto const at{data + 0x7c78 + index * 8};
    fuel_cells[index] = {{
      {source.signed_le16(at),source.signed_le16(at + 2)},
      {source.signed_le16(at + 4),source.signed_le16(at + 6)},
    }};
  }
  flight_formats = {string(0x1b80),string(0x1b88),string(0x1b8c)};
  zero_range = string(0x1b90);
  engine_formats = {string(0x1bb4),string(0x1bc0)};
  fuel_total_format = string(0x1bd4);
  speed_scale = std::bit_cast<float>(source.le32(data + 0x57a8));
  altitude_scale = std::bit_cast<float>(source.le32(data + 0x1b92));
  gauge_fuel_scale = real(0x1ba6);
  gauge_throttle_scale = std::bit_cast<float>(source.le32(data + 0x1bae));
  engine_percent = real(0x1bcb);
  for(unsigned int index{0}; index != viewports.size(); ++index) {
    unsigned int const at{data + 0x5da4 + index * 20};
    auto const panel{source.le32(at + 2)}, overlay{source.le32(at + 8)}, callback{source.le32(at + 16)};
    viewports[index] = {
      .projection_centre_y{source.signed_le16(at)},
      .panel{panel ? resource(panel) : ""},
      .overlay{overlay ? resource(overlay) : ""},
      .bottom{source.signed_le16(at + 14)},
      .callback_file{callback ? 0x70aa4 + callback : 0},
    };
  }
  for(unsigned int index{0}; index != cockpit_steps.size(); ++index) cockpit_steps[index] = source.signed_le16(data + 0x6018 + index * 2);
}

} // namespace tfx::cockpit
