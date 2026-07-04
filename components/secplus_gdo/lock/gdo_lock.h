#pragma once

#include "esphome/core/component.h"
#include "esphome/components/lock/lock.h"
#include "gdo.h"

namespace esphome {
namespace secplus_gdo {

class GDOLock : public lock::Lock, public Component {
 public:
  void set_gdo_handle(gdo_handle_t handle) { this->gdo_ = handle; }
  void set_sync_state(bool synced) { this->synced_ = synced; }

  // Reflect opener-reported lock state.
  void set_state(gdo_lock_state_t state) {
    if (state == this->lock_state_) {
      return;
    }
    this->lock_state_ = state;
    this->publish_state(state == GDO_LOCK_STATE_LOCKED ? lock::LockState::LOCK_STATE_LOCKED
                                                       : lock::LockState::LOCK_STATE_UNLOCKED);
  }

 protected:
  void control(const lock::LockCall &call) override {
    if (!this->synced_ || this->gdo_ == nullptr) {
      return;
    }
    const auto state = *call.get_state();
    if (state == lock::LockState::LOCK_STATE_LOCKED) {
      gdo_lock(this->gdo_);
    } else if (state == lock::LockState::LOCK_STATE_UNLOCKED) {
      gdo_unlock(this->gdo_);
    }
  }

  gdo_handle_t gdo_{nullptr};
  bool synced_{false};
  gdo_lock_state_t lock_state_{GDO_LOCK_STATE_MAX};
};

}  // namespace secplus_gdo
}  // namespace esphome
