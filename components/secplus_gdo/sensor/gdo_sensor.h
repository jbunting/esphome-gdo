#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"

namespace esphome {
namespace secplus_gdo {

// Read-only; the hub pushes state via a callback bound to publish_state().
class GDOSensor : public sensor::Sensor, public Component {};

}  // namespace secplus_gdo
}  // namespace esphome
