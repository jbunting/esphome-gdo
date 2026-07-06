#pragma once

#include "esphome/core/component.h"
#include "esphome/components/binary_sensor/binary_sensor.h"

namespace esphome {
namespace secplus_gdo {

// Read-only; the hub pushes state via a callback bound to publish_state().
class GDOBinarySensor : public binary_sensor::BinarySensor, public Component {};

}  // namespace secplus_gdo
}  // namespace esphome
