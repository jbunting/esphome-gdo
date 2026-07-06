# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
# Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import CONF_ID, CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOBinarySensor = secplus_gdo_ns.class_(
    "GDOBinarySensor", binary_sensor.BinarySensor, cg.Component
)
GDOBinarySensorType = secplus_gdo_ns.enum("GDOBinarySensorType", is_class=True)

TYPES = {
    "motion": GDOBinarySensorType.MOTION,
    "obstruction": GDOBinarySensorType.OBSTRUCTION,
    "motor": GDOBinarySensorType.MOTOR,
    "button": GDOBinarySensorType.BUTTON,
}

CONFIG_SCHEMA = (
    binary_sensor.binary_sensor_schema(GDOBinarySensor)
    .extend(
        {
            cv.Required(CONF_TYPE): cv.one_of(*TYPES, lower=True),
        }
    )
    .extend(SECPLUS_GDO_CONFIG_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await binary_sensor.register_binary_sensor(var, config)
    await cg.register_component(var, config)
    cg.add(var.set_type(TYPES[config[CONF_TYPE]]))
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
