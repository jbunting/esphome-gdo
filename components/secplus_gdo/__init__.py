# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jared Bunting
# Derived from gdolib and konnected-io/konnected-esphome (both GPL-3.0-or-later).

"""ESPHome external component for Chamberlain/LiftMaster Security+ garage door
openers, driven by gdolib (https://github.com/argilo/secplus + Konnected's
gdolib). This is the hub component; entities live in the cover/, light/ and
lock/ platform packages and reference the hub by id.

Multiple hubs may be declared (MULTI_CONF) — one per UART port — so a single
board can drive several openers concurrently.
"""

import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome import pins
from esphome.components.esp32 import get_esp32_variant
from esphome.components.esp32.const import (
    VARIANT_ESP32,
    VARIANT_ESP32C2,
    VARIANT_ESP32C3,
    VARIANT_ESP32C5,
    VARIANT_ESP32C6,
    VARIANT_ESP32H2,
    VARIANT_ESP32P4,
    VARIANT_ESP32S2,
    VARIANT_ESP32S3,
)
from esphome.const import CONF_ID
from esphome.core import CORE

CODEOWNERS = ["@jbunting"]
DEPENDENCIES = ["esp32", "preferences"]
MULTI_CONF = True
DOMAIN = "secplus_gdo"

secplus_gdo_ns = cg.esphome_ns.namespace("secplus_gdo")
GDOHub = secplus_gdo_ns.class_("GDOHub", cg.Component)

CONF_SECPLUS_GDO_ID = "secplus_gdo_id"
CONF_TX_PIN = "tx_pin"
CONF_RX_PIN = "rx_pin"
CONF_OBSTRUCTION_PIN = "obstruction_pin"
CONF_OBSTRUCTION_FROM_STATUS = "obstruction_from_status"
CONF_INVERT_UART = "invert_uart"
CONF_UART_NUM = "uart_num"

# Number of hardware (HP) UART controllers per ESP32 variant. UART0 is normally
# the logger console, so auto-assignment only ever hands out ports >= 1; a hub
# may still claim UART0 by setting uart_num: 0 explicitly (with the console
# disabled). Variants not listed fall back to the common minimum.
_UART_COUNTS = {
    VARIANT_ESP32: 3,
    VARIANT_ESP32S2: 2,
    VARIANT_ESP32S3: 3,
    VARIANT_ESP32C2: 2,
    VARIANT_ESP32C3: 2,
    VARIANT_ESP32C5: 2,
    VARIANT_ESP32C6: 2,
    VARIANT_ESP32H2: 2,
    VARIANT_ESP32P4: 5,
}
_DEFAULT_UART_COUNT = 2


def _validate_esp_idf(config):
    if CORE.target_framework != "esp-idf":
        raise cv.Invalid(
            "secplus_gdo requires the esp-idf framework. Set "
            "esp32: framework: type: esp-idf in your configuration."
        )
    return config


def _uart_count():
    return _UART_COUNTS.get(get_esp32_variant(), _DEFAULT_UART_COUNT)


def _resolve_uart_assignments(hubs, max_uarts):
    """Map each hub id (as str) to a UART port.

    Explicit uart_num values are honored and validated; the remaining hubs are
    auto-assigned the lowest free port >= 1 (UART0 stays free for the console).
    Raises cv.Invalid on out-of-range ports, collisions, or when there aren't
    enough ports for every hub.
    """
    taken = set()
    explicit = {}
    for hub in hubs:
        if CONF_UART_NUM not in hub:
            continue
        num = hub[CONF_UART_NUM]
        if not 0 <= num < max_uarts:
            raise cv.Invalid(
                f"uart_num {num} is out of range for this ESP32 variant "
                f"(valid 0..{max_uarts - 1})",
            )
        if num in taken:
            raise cv.Invalid(
                f"uart_num {num} is assigned to more than one secplus_gdo hub"
            )
        taken.add(num)
        explicit[str(hub[CONF_ID])] = num

    assignments = dict(explicit)
    for hub in hubs:
        hid = str(hub[CONF_ID])
        if hid in explicit:
            continue
        port = next((p for p in range(1, max_uarts) if p not in taken), None)
        if port is None:
            raise cv.Invalid(
                "Not enough free UART ports for all secplus_gdo hubs on this "
                "ESP32 variant. Free UART0 (set uart_num: 0 and disable the "
                "logger console) or use a variant with more UARTs."
            )
        taken.add(port)
        assignments[hid] = port
    return assignments


def _final_validate(config):
    hubs = fv.full_config.get().get(DOMAIN, [])
    # Raises on any range/collision/capacity problem, at `esphome config` time.
    _resolve_uart_assignments(hubs, _uart_count())
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(GDOHub),
            cv.Required(CONF_TX_PIN): pins.internal_gpio_output_pin_number,
            cv.Required(CONF_RX_PIN): pins.internal_gpio_input_pin_number,
            cv.Optional(CONF_OBSTRUCTION_PIN): pins.internal_gpio_input_pin_number,
            cv.Optional(CONF_OBSTRUCTION_FROM_STATUS, default=True): cv.boolean,
            cv.Optional(CONF_INVERT_UART, default=False): cv.boolean,
            # Optional. Omit to auto-assign from UART1 up (UART0 = console). The
            # valid range is checked per-ESP32-variant in FINAL_VALIDATE_SCHEMA.
            cv.Optional(CONF_UART_NUM): cv.int_range(min=0),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    _validate_esp_idf,
)

FINAL_VALIDATE_SCHEMA = _final_validate

# Shared schema fragment for entity platforms so they can locate their hub.
# GenerateID + use_id means a single-hub config can omit secplus_gdo_id.
SECPLUS_GDO_CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_SECPLUS_GDO_ID): cv.use_id(GDOHub),
    }
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Resolve UART assignments across all hubs (collision-free, variant-aware).
    assignments = _resolve_uart_assignments(CORE.config.get(DOMAIN, []), _uart_count())
    cg.add(var.set_uart_num(assignments[str(config[CONF_ID])]))

    cg.add(var.set_tx_pin(config[CONF_TX_PIN]))
    cg.add(var.set_rx_pin(config[CONF_RX_PIN]))
    if CONF_OBSTRUCTION_PIN in config:
        cg.add(var.set_obstruction_pin(config[CONF_OBSTRUCTION_PIN]))
    cg.add(var.set_obstruction_from_status(config[CONF_OBSTRUCTION_FROM_STATUS]))
    cg.add(var.set_invert_uart(config[CONF_INVERT_UART]))

    # The component declares its own native dependency, so consumers don't have
    # to add gdolib to lib_deps themselves.
    cg.add_library("gdolib", None, "https://github.com/jbunting/gdolib#840f634")
