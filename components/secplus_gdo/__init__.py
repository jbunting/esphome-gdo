"""ESPHome external component for Chamberlain/LiftMaster Security+ garage door
openers, driven by gdolib (https://github.com/argilo/secplus + Konnected's
gdolib). This is the hub component; entities live in the cover/, light/ and
lock/ platform packages and reference the hub by id.

Multiple hubs may be declared (MULTI_CONF) — one per UART port — so a single
board can drive several openers concurrently.
"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.const import CONF_ID
from esphome.core import CORE

CODEOWNERS = ["@jbunting"]
DEPENDENCIES = ["esp32", "preferences"]
MULTI_CONF = True

secplus_gdo_ns = cg.esphome_ns.namespace("secplus_gdo")
GDOHub = secplus_gdo_ns.class_("GDOHub", cg.Component)

# gdolib pinned to the multi-instance branch of the fork.
GDOLIB_LIB = "gdolib=https://github.com/jbunting/gdolib#840f634"

CONF_SECPLUS_GDO_ID = "secplus_gdo_id"
CONF_TX_PIN = "tx_pin"
CONF_RX_PIN = "rx_pin"
CONF_OBSTRUCTION_PIN = "obstruction_pin"
CONF_OBSTRUCTION_FROM_STATUS = "obstruction_from_status"
CONF_INVERT_UART = "invert_uart"
CONF_UART_NUM = "uart_num"

# Auto-assigned UART port for hubs that don't specify one. Starts at UART1 to
# leave UART0 for the serial console/logger.
_next_auto_uart_num = 1


def _validate_esp_idf(config):
    if CORE.target_framework != "esp-idf":
        raise cv.Invalid(
            "secplus_gdo requires the esp-idf framework. Set "
            "esp32: framework: type: esp-idf in your configuration."
        )
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
            # ESP32 variants expose 1-3 UARTs (ports 0-2); UART0 is normally the
            # console. Omit to auto-assign starting at UART1.
            cv.Optional(CONF_UART_NUM): cv.int_range(min=0, max=2),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    _validate_esp_idf,
)

# Shared schema fragment for entity platforms so they can locate their hub.
# GenerateID + use_id means a single-hub config can omit secplus_gdo_id.
SECPLUS_GDO_CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_SECPLUS_GDO_ID): cv.use_id(GDOHub),
    }
)


async def to_code(config):
    global _next_auto_uart_num

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    uart_num = config.get(CONF_UART_NUM)
    if uart_num is None:
        uart_num = _next_auto_uart_num
        _next_auto_uart_num += 1
    cg.add(var.set_uart_num(uart_num))

    cg.add(var.set_tx_pin(config[CONF_TX_PIN]))
    cg.add(var.set_rx_pin(config[CONF_RX_PIN]))
    if CONF_OBSTRUCTION_PIN in config:
        cg.add(var.set_obstruction_pin(config[CONF_OBSTRUCTION_PIN]))
    cg.add(var.set_obstruction_from_status(config[CONF_OBSTRUCTION_FROM_STATUS]))
    cg.add(var.set_invert_uart(config[CONF_INVERT_UART]))

    # The component declares its own native dependency and the linker wrap used
    # to safe the TX pin on a panic, so consumers don't have to touch lib_deps.
    cg.add_library("gdolib", None, "https://github.com/jbunting/gdolib#840f634")
    cg.add_build_flag("-Wl,--wrap=esp_panic_handler")
