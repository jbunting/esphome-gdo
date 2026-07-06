#pragma once

#include "esphome/core/component.h"
#include "esphome/components/cover/cover.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Cover entity for the garage door. gdolib handles the protocol details,
// including the toggle-only / stop-then-toggle behavior, so this class only maps
// ESPHome cover commands and gdolib door state.
class GDODoor : public cover::Cover, public Component {
 public:
  cover::CoverTraits get_traits() override;
  void control(const cover::CoverCall &call) override;

  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }
  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event);

  // Applies a door-position update. position is the ESPHome cover position
  // (1.0 = open, 0.0 = closed), or NAN if unknown.
  void set_state(gdo_door_state_t state, float position);

 protected:
  gdo_handle_t gdo_{nullptr};
  bool synced_{false};
  gdo_door_state_t state_{GDO_DOOR_STATE_UNKNOWN};
};

}  // namespace secplus_gdo
}  // namespace esphome
