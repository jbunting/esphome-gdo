#pragma once

#include <functional>
#include <utility>
#include <vector>

#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Persisted Security+ 2.0 credentials. client_id is normally constant; the
// rolling code advances with every command and must survive reboots.
struct GDOCredentials {
  uint32_t client_id;
  uint32_t rolling_code;
} __attribute__((packed));

// One hub per garage door opener. Owns the gdolib context for a single UART
// port and bridges gdolib events to the ESPHome entities.
//
// The hub is deliberately decoupled from the concrete entity classes: entities
// register callbacks (built in each platform's codegen, so they are compiled in
// main.cpp where the entity headers are available). This means the hub never
// #includes the entity headers, so a configuration that uses only some of the
// platforms still compiles — ESPHome only copies the used platform directories.
class GDOHub : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  void on_shutdown() override;

  // Run before the entity platforms so the context exists and the handle has
  // been distributed before any child's setup() restores settings into it.
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
  // Called once during setup(), before entity setup(), with the gdolib handle.
  void add_handle_listener(std::function<void(gdo_handle_t)> f) {
    this->handle_listeners_.push_back(std::move(f));
  }
  // Called on every gdolib event; each entity filters for what it cares about.
  void add_event_listener(std::function<void(const gdo_status_t *, gdo_cb_event_t)> f) {
    this->event_listeners_.push_back(std::move(f));
  }

  // Dispatched from the gdolib C event callback (see .cpp).
  void handle_event(const gdo_status_t *status, gdo_cb_event_t event);

 protected:
  gdo_handle_t gdo_{nullptr};
  uint8_t uart_num_{1};
  int8_t tx_pin_{-1};
  int8_t rx_pin_{-1};
  int8_t obst_pin_{-1};
  bool obst_from_status_{true};
  bool invert_uart_{false};
  bool started_{false};

  std::vector<std::function<void(gdo_handle_t)>> handle_listeners_;
  std::vector<std::function<void(const gdo_status_t *, gdo_cb_event_t)>> event_listeners_;

  // Hub owns credential persistence so a Sec+ 2.0 opener keeps accepting
  // commands across reboots even with no client_id/rolling_code entities.
  ESPPreferenceObject cred_pref_;
  GDOCredentials saved_creds_{};
  bool have_saved_creds_{false};
  uint32_t last_cred_check_ms_{0};
};

}  // namespace secplus_gdo
}  // namespace esphome
