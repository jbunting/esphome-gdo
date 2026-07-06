# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
# Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.const import CONF_ID, CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOSwitch = secplus_gdo_ns.class_("GDOSwitch", switch.Switch, cg.Component)
GDOSwitchType = secplus_gdo_ns.enum("GDOSwitchType", is_class=True)

TYPES = {
    "learn": ("register_learn", GDOSwitchType.LEARN),
    "toggle_only": ("register_toggle_only", GDOSwitchType.TOGGLE_ONLY),
}

CONFIG_SCHEMA = (
    switch.switch_schema(GDOSwitch)
    .extend(
        {
            cv.Required(CONF_TYPE): cv.one_of(*TYPES, lower=True),
        }
    )
    .extend(SECPLUS_GDO_CONFIG_SCHEMA)
)


async def to_code(config):
    register, enum_value = TYPES[config[CONF_TYPE]]
    var = cg.new_Pvariable(config[CONF_ID])
    await switch.register_switch(var, config)
    await cg.register_component(var, config)
    cg.add(var.set_type(enum_value))
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(hub.add_handle_listener(cg.RawExpression(f"[](gdo_handle_t h) {{ {var}->set_gdo_handle(h); }}")))
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
