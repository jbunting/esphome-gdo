#pragma once

#include "esphome/core/component.h"
#include "esphome/components/light/light_output.h"
#include "esphome/components/light/light_state.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Binary (on/off) light for the opener's built-in light.
class GDOLight : public Component, public light::LightOutput {
 public:
  light::LightTraits get_traits() override {
    auto traits = light::LightTraits();
    traits.set_supported_color_modes({light::ColorMode::ON_OFF});
    return traits;
  }

  void setup_state(light::LightState *state) override { this->state_ = state; }

  void write_state(light::LightState *state) override {
    if (!this->synced_ || this->gdo_ == nullptr) {
      return;
    }
    bool binary;
    state->current_values_as_binary(&binary);
    if (binary) {
      gdo_light_on(this->gdo_);
    } else {
      gdo_light_off(this->gdo_);
    }
  }

  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }

  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event) {
    if (event == GDO_CB_EVENT_SYNCED) {
      this->synced_ = status->synced;
    } else if (event == GDO_CB_EVENT_LIGHT) {
      this->set_state(status->light);
    }
  }

  // Reflect opener-reported state without re-issuing a command (mutating the
  // values directly instead of make_call() avoids a feedback loop back to
  // write_state()).
  void set_state(gdo_light_state_t state) {
    if (state == this->light_state_ || this->state_ == nullptr) {
      return;
    }
    this->light_state_ = state;
    const bool is_on = state == GDO_LIGHT_STATE_ON;
    this->state_->current_values.set_state(is_on);
    this->state_->remote_values.set_state(is_on);
    this->state_->publish_state();
  }

 protected:
  gdo_handle_t gdo_{nullptr};
  light::LightState *state_{nullptr};
  bool synced_{false};
  gdo_light_state_t light_state_{GDO_LIGHT_STATE_MAX};
};

}  // namespace secplus_gdo
}  // namespace esphome
