#pragma once

#include "esphome/core/component.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

enum class GDOBinarySensorType { MOTION, OBSTRUCTION, MOTOR, BUTTON };

// Read-only; the hub calls on_gdo_event() for every gdolib event and this
// filters for the one that matches its configured type.
class GDOBinarySensor : public binary_sensor::BinarySensor, public Component {
 public:
  void set_type(GDOBinarySensorType type) { this->type_ = type; }

  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event) {
    switch (this->type_) {
      case GDOBinarySensorType::MOTION:
        if (event == GDO_CB_EVENT_MOTION) {
          this->publish_state(status->motion == GDO_MOTION_STATE_DETECTED);
        }
        break;
      case GDOBinarySensorType::OBSTRUCTION:
        if (event == GDO_CB_EVENT_OBSTRUCTION) {
          this->publish_state(status->obstruction == GDO_OBSTRUCTION_STATE_OBSTRUCTED);
        }
        break;
      case GDOBinarySensorType::MOTOR:
        if (event == GDO_CB_EVENT_MOTOR) {
          this->publish_state(status->motor == GDO_MOTOR_STATE_ON);
        }
        break;
      case GDOBinarySensorType::BUTTON:
        if (event == GDO_CB_EVENT_BUTTON) {
          this->publish_state(status->button == GDO_BUTTON_STATE_PRESSED);
        }
        break;
    }
  }

 protected:
  GDOBinarySensorType type_{GDOBinarySensorType::MOTION};
};

}  // namespace secplus_gdo
}  // namespace esphome
