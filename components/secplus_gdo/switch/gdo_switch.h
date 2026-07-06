#pragma once

#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "esphome/components/switch/switch.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

enum class GDOSwitchType { LEARN, TOGGLE_ONLY };

class GDOSwitch : public switch_::Switch, public Component {
 public:
  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }
  void set_type(GDOSwitchType type) { this->type_ = type; }

  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event) {
    if (this->type_ == GDOSwitchType::LEARN && event == GDO_CB_EVENT_LEARN) {
      this->publish_state(status->learn == GDO_LEARN_STATE_ACTIVE);
    }
  }

  void setup() override {
    // Toggle-only is a persisted setting restored into the context before start.
    // Learn is momentary and intentionally not restored.
    if (this->type_ == GDOSwitchType::TOGGLE_ONLY) {
      this->pref_ = global_preferences->make_preference<bool>(this->get_object_id_hash());
      bool value = false;
      if (this->pref_.load(&value)) {
        this->write_state(value);
      }
    }
  }

  void write_state(bool state) override {
    if (this->gdo_ != nullptr) {
      if (this->type_ == GDOSwitchType::LEARN) {
        if (state) {
          gdo_activate_learn(this->gdo_);
        } else {
          gdo_deactivate_learn(this->gdo_);
        }
      } else {  // TOGGLE_ONLY
        gdo_set_toggle_only(this->gdo_, state);
      }
    }
    if (this->type_ == GDOSwitchType::TOGGLE_ONLY) {
      this->pref_.save(&state);
    }
    this->publish_state(state);
  }

 protected:
  gdo_handle_t gdo_{nullptr};
  GDOSwitchType type_{GDOSwitchType::LEARN};
  ESPPreferenceObject pref_;
};

}  // namespace secplus_gdo
}  // namespace esphome
