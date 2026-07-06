# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
# Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import cover
from esphome.const import CONF_ID

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDODoor = secplus_gdo_ns.class_("GDODoor", cover.Cover, cg.Component)

CONFIG_SCHEMA = cover.cover_schema(GDODoor).extend(SECPLUS_GDO_CONFIG_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await cover.register_cover(var, config)
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(hub.add_handle_listener(cg.RawExpression(f"[](gdo_handle_t h) {{ {var}->set_gdo_handle(h); }}")))
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
