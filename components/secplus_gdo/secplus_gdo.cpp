#include "secplus_gdo.h"

#include <cmath>
#include <string>
#include <vector>

#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

#include "cover/gdo_door.h"
#include "light/gdo_light.h"
#include "lock/gdo_lock.h"

namespace esphome {
namespace secplus_gdo {

static const char *const TAG = "secplus_gdo";

// How often loop() checks the rolling code and flushes it to NVS when changed.
static const uint32_t ROLLING_CODE_SAVE_INTERVAL_MS = 5000;

// TX pins of every hub, disabled by the panic-handler wrap below so a crash
// cannot leave a pin driving the opener open. Populated in setup().
static std::vector<uint8_t> g_gdo_tx_pins;  // NOLINT(runtime/global-variables)

// gdolib invokes this from its task; forward to the owning hub instance.
static void gdo_event_callback(const gdo_status_t *status, gdo_cb_event_t event, void *arg) {
  static_cast<GDOHub *>(arg)->handle_event(status, event);
}

void GDOHub::setup() {
  gdo_config_t conf = {
      .uart_num = static_cast<uart_port_t>(this->uart_num_),
      .obst_from_status = this->obst_from_status_,
      .invert_uart = this->invert_uart_,
      .uart_tx_pin = static_cast<gpio_num_t>(this->tx_pin_),
      .uart_rx_pin = static_cast<gpio_num_t>(this->rx_pin_),
      .obst_in_pin = static_cast<gpio_num_t>(this->obst_pin_),
  };

  esp_err_t err = gdo_init(&conf, &this->gdo_);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "gdo_init failed on UART%u: %s", this->uart_num_, esp_err_to_name(err));
    this->mark_failed();
    return;
  }

  // Restore the persisted Security+ v2 rolling code (keyed per UART so multiple
  // hubs don't collide) before starting, while the context is still unsynced.
  uint32_t hash = fnv1_hash(std::string("secplus_gdo_rolling_code_") + std::to_string(this->uart_num_));
  this->rolling_code_pref_ = global_preferences->make_preference<uint32_t>(hash);
  uint32_t restored = 0;
  if (this->rolling_code_pref_.load(&restored)) {
    gdo_set_rolling_code(this->gdo_, restored);
    this->saved_rolling_code_ = restored;
    ESP_LOGD(TAG, "Restored rolling code %" PRIu32, restored);
  }

  // Register the TX pin for the panic-handler safeing wrap.
  g_gdo_tx_pins.push_back(static_cast<uint8_t>(this->tx_pin_));

  // Hand the context to the entities before their setup() runs.
  if (this->door_ != nullptr) {
    this->door_->set_gdo_handle(this->gdo_);
  }
  if (this->light_ != nullptr) {
    this->light_->set_gdo_handle(this->gdo_);
  }
  if (this->lock_ != nullptr) {
    this->lock_->set_gdo_handle(this->gdo_);
  }

  err = gdo_start(this->gdo_, gdo_event_callback, this);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "gdo_start failed on UART%u: %s", this->uart_num_, esp_err_to_name(err));
    this->mark_failed();
    return;
  }
  this->started_ = true;
  ESP_LOGI(TAG, "secplus_gdo started on UART%u", this->uart_num_);
}

void GDOHub::loop() {
  if (!this->started_) {
    return;
  }

  // Throttled: flush the rolling code to NVS when it advances.
  const uint32_t now = millis();
  if (now - this->last_rolling_code_check_ms_ < ROLLING_CODE_SAVE_INTERVAL_MS) {
    return;
  }
  this->last_rolling_code_check_ms_ = now;

  gdo_status_t status;
  if (gdo_get_status(this->gdo_, &status) == ESP_OK && status.rolling_code != this->saved_rolling_code_) {
    this->saved_rolling_code_ = status.rolling_code;
    this->rolling_code_pref_.save(&this->saved_rolling_code_);
  }
}

void GDOHub::on_shutdown() {
  if (this->gdo_ == nullptr) {
    return;
  }
  gdo_status_t status;
  if (gdo_get_status(this->gdo_, &status) == ESP_OK) {
    this->rolling_code_pref_.save(&status.rolling_code);
  }
  gdo_deinit(this->gdo_);
  this->gdo_ = nullptr;
}

void GDOHub::set_children_sync_state_(bool synced) {
  if (this->door_ != nullptr) {
    this->door_->set_sync_state(synced);
  }
  if (this->light_ != nullptr) {
    this->light_->set_sync_state(synced);
  }
  if (this->lock_ != nullptr) {
    this->lock_->set_sync_state(synced);
  }
}

void GDOHub::handle_event(const gdo_status_t *status, gdo_cb_event_t event) {
  switch (event) {
    case GDO_CB_EVENT_SYNCED:
      ESP_LOGI(TAG, "Synced: %s, protocol: %s", status->synced ? "true" : "false",
               gdo_protocol_type_to_string(status->protocol));
      if (!status->synced) {
        // Rolling code drifted; bump and retry (gdolib rejects otherwise).
        if (gdo_set_rolling_code(this->gdo_, status->rolling_code + 100) == ESP_OK) {
          gdo_sync(this->gdo_);
        }
      } else {
        this->saved_rolling_code_ = status->rolling_code;
        this->rolling_code_pref_.save(&this->saved_rolling_code_);
      }
      this->set_children_sync_state_(status->synced);
      break;

    case GDO_CB_EVENT_LIGHT:
      if (this->light_ != nullptr) {
        this->light_->set_state(status->light);
      }
      break;

    case GDO_CB_EVENT_LOCK:
      if (this->lock_ != nullptr) {
        this->lock_->set_state(status->lock);
      }
      break;

    case GDO_CB_EVENT_DOOR_POSITION:
      if (this->door_ != nullptr) {
        // gdolib: 0 = open, 10000 = closed, -1 = unknown.
        // ESPHome cover: 1.0 = open, 0.0 = closed.
        float position =
            status->door_position < 0 ? NAN : static_cast<float>(10000 - status->door_position) / 10000.0f;
        this->door_->set_state(status->door, position);
      }
      break;

    default:
      break;
  }
}

void GDOHub::dump_config() {
  ESP_LOGCONFIG(TAG, "Security+ GDO hub:");
  ESP_LOGCONFIG(TAG, "  UART port: %u", this->uart_num_);
  ESP_LOGCONFIG(TAG, "  TX pin: GPIO%d", this->tx_pin_);
  ESP_LOGCONFIG(TAG, "  RX pin: GPIO%d", this->rx_pin_);
  if (this->obst_pin_ >= 0) {
    ESP_LOGCONFIG(TAG, "  Obstruction pin: GPIO%d", this->obst_pin_);
  }
  ESP_LOGCONFIG(TAG, "  Obstruction from status: %s", YESNO(this->obst_from_status_));
  ESP_LOGCONFIG(TAG, "  Invert UART: %s", YESNO(this->invert_uart_));
}

}  // namespace secplus_gdo
}  // namespace esphome

// Wrap the panic handler so a crash cannot leave any GDO TX pin driving the
// opener. Reconfigure every registered TX pin as a pulled-down input, then fall
// through to the real handler.
extern "C" {
#include "driver/gpio.h"
#include "hal/gpio_hal.h"

void __real_esp_panic_handler(void *info);

void __wrap_esp_panic_handler(void *info) {
  for (uint8_t pin : esphome::secplus_gdo::g_gdo_tx_pins) {
    gpio_hal_iomux_func_sel(GPIO_PIN_MUX_REG[pin], PIN_FUNC_GPIO);
    gpio_set_direction(static_cast<gpio_num_t>(pin), GPIO_MODE_INPUT);
    gpio_pulldown_en(static_cast<gpio_num_t>(pin));
  }
  __real_esp_panic_handler(info);
}
}  // extern "C"
