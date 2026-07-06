#include "secplus_gdo.h"

#include <cinttypes>
#include <cmath>
#include <string>

#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

#include "cover/gdo_door.h"
#include "light/gdo_light.h"
#include "lock/gdo_lock.h"
#include "number/gdo_number.h"
#include "select/gdo_select.h"
#include "switch/gdo_switch.h"

namespace esphome {
namespace secplus_gdo {

static const char *const TAG = "secplus_gdo";

// How often loop() polls the credentials and flushes them to NVS when changed.
static const uint32_t CRED_SAVE_INTERVAL_MS = 5000;

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

  // Restore persisted credentials (keyed per UART) before start, while the
  // context is still unsynced.
  uint32_t hash = fnv1_hash(std::string("secplus_gdo_creds_") + std::to_string(this->uart_num_));
  this->cred_pref_ = global_preferences->make_preference<GDOCredentials>(hash);
  if (this->cred_pref_.load(&this->saved_creds_)) {
    this->have_saved_creds_ = true;
    gdo_set_client_id(this->gdo_, this->saved_creds_.client_id);
    gdo_set_rolling_code(this->gdo_, this->saved_creds_.rolling_code);
    ESP_LOGD(TAG, "Restored client_id=0x%" PRIx32 ", rolling_code=%" PRIu32, this->saved_creds_.client_id,
             this->saved_creds_.rolling_code);
  }

  // Hand the context to the entities before their setup() runs.
  this->distribute_handle_();

  // gdo_start() is deferred to the first loop() so the entity platforms can push
  // their saved settings (protocol, durations, toggle-only) into the context
  // first — those setters must run before the sync handshake.
}

void GDOHub::loop() {
  if (this->gdo_ == nullptr) {
    return;
  }

  if (!this->started_) {
    esp_err_t err = gdo_start(this->gdo_, gdo_event_callback, this);
    if (err != ESP_OK) {
      ESP_LOGE(TAG, "gdo_start failed on UART%u: %s", this->uart_num_, esp_err_to_name(err));
      this->mark_failed();
      return;
    }
    this->started_ = true;
    ESP_LOGI(TAG, "secplus_gdo started on UART%u", this->uart_num_);
    return;
  }

  // Throttled: flush credentials to NVS when they advance.
  const uint32_t now = millis();
  if (now - this->last_cred_check_ms_ < CRED_SAVE_INTERVAL_MS) {
    return;
  }
  this->last_cred_check_ms_ = now;

  gdo_status_t status;
  if (gdo_get_status(this->gdo_, &status) == ESP_OK &&
      (status.client_id != this->saved_creds_.client_id || status.rolling_code != this->saved_creds_.rolling_code)) {
    this->saved_creds_.client_id = status.client_id;
    this->saved_creds_.rolling_code = status.rolling_code;
    this->cred_pref_.save(&this->saved_creds_);
  }
}

void GDOHub::on_shutdown() {
  if (this->gdo_ == nullptr) {
    return;
  }
  gdo_status_t status;
  if (gdo_get_status(this->gdo_, &status) == ESP_OK) {
    GDOCredentials creds{status.client_id, status.rolling_code};
    this->cred_pref_.save(&creds);
  }
  gdo_deinit(this->gdo_);
  this->gdo_ = nullptr;
}

void GDOHub::distribute_handle_() {
  if (this->door_ != nullptr) {
    this->door_->set_gdo_handle(this->gdo_);
  }
  if (this->light_ != nullptr) {
    this->light_->set_gdo_handle(this->gdo_);
  }
  if (this->lock_ != nullptr) {
    this->lock_->set_gdo_handle(this->gdo_);
  }
  if (this->protocol_select_ != nullptr) {
    this->protocol_select_->set_gdo_handle(this->gdo_);
  }
  if (this->learn_switch_ != nullptr) {
    this->learn_switch_->set_gdo_handle(this->gdo_);
  }
  if (this->toggle_only_switch_ != nullptr) {
    this->toggle_only_switch_->set_gdo_handle(this->gdo_);
  }
  if (this->open_duration_ != nullptr) {
    this->open_duration_->set_gdo_handle(this->gdo_);
  }
  if (this->close_duration_ != nullptr) {
    this->close_duration_->set_gdo_handle(this->gdo_);
  }
  if (this->client_id_number_ != nullptr) {
    this->client_id_number_->set_gdo_handle(this->gdo_);
  }
  if (this->rolling_code_number_ != nullptr) {
    this->rolling_code_number_->set_gdo_handle(this->gdo_);
  }
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
        this->saved_creds_.client_id = status->client_id;
        this->saved_creds_.rolling_code = status->rolling_code;
        this->cred_pref_.save(&this->saved_creds_);
        if (this->protocol_select_ != nullptr) {
          this->protocol_select_->update_state(status->protocol);
        }
        if (this->client_id_number_ != nullptr) {
          this->client_id_number_->update_state(static_cast<float>(status->client_id));
        }
        if (this->rolling_code_number_ != nullptr) {
          this->rolling_code_number_->update_state(static_cast<float>(status->rolling_code));
        }
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

    case GDO_CB_EVENT_MOTION:
      if (this->on_motion_) {
        this->on_motion_(status->motion == GDO_MOTION_STATE_DETECTED);
      }
      break;

    case GDO_CB_EVENT_OBSTRUCTION:
      if (this->on_obstruction_) {
        this->on_obstruction_(status->obstruction == GDO_OBSTRUCTION_STATE_OBSTRUCTED);
      }
      break;

    case GDO_CB_EVENT_MOTOR:
      if (this->on_motor_) {
        this->on_motor_(status->motor == GDO_MOTOR_STATE_ON);
      }
      break;

    case GDO_CB_EVENT_BUTTON:
      if (this->on_button_) {
        this->on_button_(status->button == GDO_BUTTON_STATE_PRESSED);
      }
      break;

    case GDO_CB_EVENT_OPENINGS:
      if (this->on_openings_) {
        this->on_openings_(static_cast<float>(status->openings));
      }
      break;

    case GDO_CB_EVENT_TTC:
      if (this->on_ttc_) {
        this->on_ttc_(static_cast<float>(status->ttc_seconds));
      }
      break;

    case GDO_CB_EVENT_LEARN:
      if (this->learn_switch_ != nullptr) {
        this->learn_switch_->publish_state(status->learn == GDO_LEARN_STATE_ACTIVE);
      }
      break;

    case GDO_CB_EVENT_OPEN_DURATION_MEASUREMENT:
      if (this->open_duration_ != nullptr) {
        this->open_duration_->update_state(static_cast<float>(status->open_ms));
      }
      break;

    case GDO_CB_EVENT_CLOSE_DURATION_MEASUREMENT:
      if (this->close_duration_ != nullptr) {
        this->close_duration_->update_state(static_cast<float>(status->close_ms));
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
