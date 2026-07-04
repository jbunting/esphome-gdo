#include "gdo_door.h"

#include <cmath>

#include "esphome/core/log.h"

namespace esphome {
namespace secplus_gdo {

static const char *const TAG = "secplus_gdo.cover";

cover::CoverTraits GDODoor::get_traits() {
  auto traits = cover::CoverTraits();
  traits.set_supports_stop(true);
  traits.set_supports_toggle(true);
  traits.set_supports_position(true);
  return traits;
}

void GDODoor::control(const cover::CoverCall &call) {
  if (!this->synced_ || this->gdo_ == nullptr) {
    // Re-publish so the front end reverts an optimistic command.
    this->publish_state(false);
    return;
  }

  if (call.get_stop()) {
    gdo_door_stop(this->gdo_);
    return;
  }

  if (call.get_toggle().has_value() && *call.get_toggle()) {
    gdo_door_toggle(this->gdo_);
    return;
  }

  if (call.get_position().has_value()) {
    const float pos = *call.get_position();
    if (pos >= cover::COVER_OPEN) {
      gdo_door_open(this->gdo_);
    } else if (pos <= cover::COVER_CLOSED) {
      gdo_door_close(this->gdo_);
    } else {
      // ESPHome 1.0=open..0.0=closed  ->  gdolib 0=open..10000=closed
      gdo_door_move_to_target(this->gdo_, static_cast<uint32_t>((1.0f - pos) * 10000.0f));
    }
  }
}

void GDODoor::set_state(gdo_door_state_t state, float position) {
  if (!std::isnan(position)) {
    this->position = position;
  }

  switch (state) {
    case GDO_DOOR_STATE_OPENING:
      this->current_operation = cover::COVER_OPERATION_OPENING;
      break;
    case GDO_DOOR_STATE_CLOSING:
      this->current_operation = cover::COVER_OPERATION_CLOSING;
      break;
    case GDO_DOOR_STATE_OPEN:
    case GDO_DOOR_STATE_CLOSED:
    case GDO_DOOR_STATE_STOPPED:
    default:
      this->current_operation = cover::COVER_OPERATION_IDLE;
      break;
  }

  this->state_ = state;
  this->publish_state(false);
}

}  // namespace secplus_gdo
}  // namespace esphome
