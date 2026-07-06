#pragma once

#include <string>

#include "esphome/core/application.h"
#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "esphome/components/select/select.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Protocol selector. The option list order matches gdo_protocol_type_t:
// index 0 = auto (unforced), 1 = Sec+ v1, 2 = Sec+ v2, 3 = Sec+ v1 smart panel.
class GDOSelect : public select::Select, public Component {
 public:
  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }
  void set_initial_option(const std::string &option) { this->initial_option_ = option; }

  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event) {
    if (event == GDO_CB_EVENT_SYNCED && status->synced) {
      this->update_state(status->protocol);
    }
  }

  void setup() override {
    this->pref_ = global_preferences->make_preference<size_t>(this->get_object_id_hash());
    size_t index;
    std::string value;
    if (!this->pref_.load(&index) || !this->has_index(index)) {
      value = this->initial_option_;
    } else {
      this->saved_index_ = index;
      value = this->at(index).value();
    }
    this->control(value);
  }

  void update_state(gdo_protocol_type_t protocol) {
    if (!this->has_index(protocol)) {
      return;
    }
    size_t index = protocol;
    if (index != this->saved_index_) {
      this->saved_index_ = index;
      this->pref_.save(&this->saved_index_);
    }
    this->publish_state(this->at(index).value());
  }

 protected:
  void control(const std::string &value) override {
    auto idx = this->index_of(value);
    if (!idx.has_value()) {
      return;
    }
    gdo_protocol_type_t protocol = static_cast<gdo_protocol_type_t>(idx.value());
    this->update_state(protocol);
    // Runs during setup() (before gdo_start) to restore the saved protocol. If
    // called later, gdolib rejects a protocol change once locked in, so reboot to
    // apply the new selection cleanly.
    if (this->gdo_ != nullptr && gdo_set_protocol(this->gdo_, protocol) != ESP_OK) {
      App.safe_reboot();
    }
  }

  gdo_handle_t gdo_{nullptr};
  std::string initial_option_;
  size_t saved_index_{0};
  ESPPreferenceObject pref_;
};

}  // namespace secplus_gdo
}  // namespace esphome
