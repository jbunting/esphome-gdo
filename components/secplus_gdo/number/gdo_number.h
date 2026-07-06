#pragma once

#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "esphome/components/number/number.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

enum class GDONumberType {
  OPEN_DURATION,
  CLOSE_DURATION,
  CLIENT_ID,
  ROLLING_CODE,
};

class GDONumber : public number::Number, public Component {
 public:
  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }
  void set_type(GDONumberType type) { this->type_ = type; }

  void setup() override {
    // Durations are user-tunable settings persisted here and pushed into the
    // context before start. client_id/rolling_code are runtime state persisted
    // by the hub, so those number entities are display + manual-override only.
    if (this->is_duration_()) {
      this->pref_ = global_preferences->make_preference<float>(this->get_object_id_hash());
      float value = 0;
      if (this->pref_.load(&value) && value > 0) {
        this->control(value);
      }
    }
  }

  void update_state(float value) {
    if (value == this->state) {
      return;
    }
    this->publish_state(value);
    if (this->is_duration_()) {
      this->pref_.save(&value);
    }
  }

  void control(float value) override {
    if (this->gdo_ == nullptr) {
      return;
    }
    esp_err_t err = ESP_ERR_INVALID_ARG;
    switch (this->type_) {
      case GDONumberType::OPEN_DURATION:
        err = gdo_set_open_duration(this->gdo_, static_cast<uint16_t>(value));
        break;
      case GDONumberType::CLOSE_DURATION:
        err = gdo_set_close_duration(this->gdo_, static_cast<uint16_t>(value));
        break;
      case GDONumberType::CLIENT_ID:
        err = gdo_set_client_id(this->gdo_, static_cast<uint32_t>(value));
        break;
      case GDONumberType::ROLLING_CODE:
        err = gdo_set_rolling_code(this->gdo_, static_cast<uint32_t>(value));
        break;
    }
    if (err == ESP_OK) {
      this->update_state(value);
    }
  }

 protected:
  bool is_duration_() const {
    return this->type_ == GDONumberType::OPEN_DURATION || this->type_ == GDONumberType::CLOSE_DURATION;
  }

  gdo_handle_t gdo_{nullptr};
  GDONumberType type_{GDONumberType::OPEN_DURATION};
  ESPPreferenceObject pref_;
};

}  // namespace secplus_gdo
}  // namespace esphome
