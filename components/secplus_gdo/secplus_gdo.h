#pragma once

#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Forward declarations of the entity platforms; each is registered with the hub
// and receives the gdolib handle once it is created.
class GDODoor;
class GDOLight;
class GDOLock;

// One hub per garage door opener. Owns the gdolib context (gdo_handle_t) for a
// single UART port and bridges gdolib events to the ESPHome entities.
class GDOHub : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  void on_shutdown() override;

  // Run before the entity platforms so the gdolib context exists and the handle
  // has been distributed before any child's setup() runs.
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

  // --- configuration (called from codegen) ---
  void set_uart_num(uint8_t num) { this->uart_num_ = num; }
  void set_tx_pin(uint8_t pin) { this->tx_pin_ = pin; }
  void set_rx_pin(uint8_t pin) { this->rx_pin_ = pin; }
  void set_obstruction_pin(uint8_t pin) { this->obst_pin_ = pin; }
  void set_obstruction_from_status(bool value) { this->obst_from_status_ = value; }
  void set_invert_uart(bool value) { this->invert_uart_ = value; }

  gdo_handle_t handle() const { return this->gdo_; }

  // --- entity registration (called from codegen) ---
  void register_door(GDODoor *door) { this->door_ = door; }
  void register_light(GDOLight *light) { this->light_ = light; }
  void register_lock(GDOLock *lock) { this->lock_ = lock; }

  // Dispatched from the gdolib C event callback (see .cpp).
  void handle_event(const gdo_status_t *status, gdo_cb_event_t event);

 protected:
  void set_children_sync_state_(bool synced);

  gdo_handle_t gdo_{nullptr};
  uint8_t uart_num_{1};
  int8_t tx_pin_{-1};
  int8_t rx_pin_{-1};
  int8_t obst_pin_{-1};
  bool obst_from_status_{true};
  bool invert_uart_{false};
  bool started_{false};

  GDODoor *door_{nullptr};
  GDOLight *light_{nullptr};
  GDOLock *lock_{nullptr};

  // Persist the Security+ v2 rolling code so the opener keeps accepting commands
  // across reboots without a fresh (slow, sometimes lossy) resync.
  ESPPreferenceObject rolling_code_pref_;
  uint32_t saved_rolling_code_{0};
  uint32_t last_rolling_code_check_ms_{0};
};

}  // namespace secplus_gdo
}  // namespace esphome
