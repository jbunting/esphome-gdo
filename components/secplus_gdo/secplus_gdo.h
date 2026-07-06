#pragma once

#include <functional>
#include <utility>

#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

// Entity platforms registered with the hub. Cover/light/lock/select/switch/
// number need the gdolib handle; the read-only sensors are driven via callbacks.
class GDODoor;
class GDOLight;
class GDOLock;
class GDOSelect;
class GDOSwitch;
class GDONumber;

// Persisted Security+ 2.0 credentials. client_id is normally constant; the
// rolling code advances with every command and must survive reboots.
struct GDOCredentials {
  uint32_t client_id;
  uint32_t rolling_code;
} __attribute__((packed));

// One hub per garage door opener. Owns the gdolib context for a single UART
// port and bridges gdolib events to the ESPHome entities.
class GDOHub : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  void on_shutdown() override;

  // Run before the entity platforms so the gdolib context exists and the handle
  // has been distributed before any child's setup() restores settings into it.
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
  void register_protocol_select(GDOSelect *select) { this->protocol_select_ = select; }
  void register_learn(GDOSwitch *sw) { this->learn_switch_ = sw; }
  void register_toggle_only(GDOSwitch *sw) { this->toggle_only_switch_ = sw; }
  void register_open_duration(GDONumber *n) { this->open_duration_ = n; }
  void register_close_duration(GDONumber *n) { this->close_duration_ = n; }
  void register_client_id(GDONumber *n) { this->client_id_number_ = n; }
  void register_rolling_code(GDONumber *n) { this->rolling_code_number_ = n; }

  // Read-only sensors: bound to <entity>::publish_state by codegen.
  void register_motion(std::function<void(bool)> f) { this->on_motion_ = std::move(f); }
  void register_obstruction(std::function<void(bool)> f) { this->on_obstruction_ = std::move(f); }
  void register_motor(std::function<void(bool)> f) { this->on_motor_ = std::move(f); }
  void register_button(std::function<void(bool)> f) { this->on_button_ = std::move(f); }
  void register_openings(std::function<void(float)> f) { this->on_openings_ = std::move(f); }
  void register_ttc(std::function<void(float)> f) { this->on_ttc_ = std::move(f); }

  // Dispatched from the gdolib C event callback (see .cpp).
  void handle_event(const gdo_status_t *status, gdo_cb_event_t event);

 protected:
  void distribute_handle_();
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
  GDOSelect *protocol_select_{nullptr};
  GDOSwitch *learn_switch_{nullptr};
  GDOSwitch *toggle_only_switch_{nullptr};
  GDONumber *open_duration_{nullptr};
  GDONumber *close_duration_{nullptr};
  GDONumber *client_id_number_{nullptr};
  GDONumber *rolling_code_number_{nullptr};

  std::function<void(bool)> on_motion_{nullptr};
  std::function<void(bool)> on_obstruction_{nullptr};
  std::function<void(bool)> on_motor_{nullptr};
  std::function<void(bool)> on_button_{nullptr};
  std::function<void(float)> on_openings_{nullptr};
  std::function<void(float)> on_ttc_{nullptr};

  // Hub owns credential persistence so a Sec+ 2.0 opener keeps accepting
  // commands across reboots even with no client_id/rolling_code entities.
  ESPPreferenceObject cred_pref_;
  GDOCredentials saved_creds_{};
  bool have_saved_creds_{false};
  uint32_t last_cred_check_ms_{0};
};

}  // namespace secplus_gdo
}  // namespace esphome
