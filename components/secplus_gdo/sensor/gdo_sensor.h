// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Jared Bunting
// Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

enum class GDOSensorType { OPENINGS, TIME_TO_CLOSE };

// Read-only; the hub calls on_gdo_event() for every gdolib event and this
// filters for the one that matches its configured type.
class GDOSensor : public sensor::Sensor, public Component {
 public:
  void set_type(GDOSensorType type) { this->type_ = type; }

  void on_gdo_event(const gdo_status_t *status, gdo_cb_event_t event) {
    if (this->type_ == GDOSensorType::OPENINGS && event == GDO_CB_EVENT_OPENINGS) {
      this->publish_state(status->openings);
    } else if (this->type_ == GDOSensorType::TIME_TO_CLOSE && event == GDO_CB_EVENT_TTC) {
      this->publish_state(status->ttc_seconds);
    }
  }

 protected:
  GDOSensorType type_{GDOSensorType::OPENINGS};
};

}  // namespace secplus_gdo
}  // namespace esphome
