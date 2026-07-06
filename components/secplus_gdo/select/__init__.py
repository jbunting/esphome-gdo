# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
# Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOSelect = secplus_gdo_ns.class_("GDOSelect", select.Select, cg.Component)

CONF_INITIAL_OPTION = "initial_option"

# Order matters: list index == gdo_protocol_type_t value.
PROTOCOL_OPTIONS = ["auto", "secplus_v1", "secplus_v2", "secplus_v1_with_smart_panel"]

CONFIG_SCHEMA = (
    select.select_schema(GDOSelect)
    .extend(
        {
            cv.Optional(CONF_INITIAL_OPTION, default="auto"): cv.one_of(
                *PROTOCOL_OPTIONS, lower=True
            ),
        }
    )
    .extend(SECPLUS_GDO_CONFIG_SCHEMA)
)


async def to_code(config):
    var = await select.new_select(config, options=PROTOCOL_OPTIONS)
    await cg.register_component(var, config)
    cg.add(var.set_initial_option(config[CONF_INITIAL_OPTION]))
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(hub.add_handle_listener(cg.RawExpression(f"[](gdo_handle_t h) {{ {var}->set_gdo_handle(h); }}")))
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
