import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import number
from esphome.const import CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDONumber = secplus_gdo_ns.class_("GDONumber", number.Number, cg.Component)
GDONumberType = secplus_gdo_ns.enum("GDONumberType", is_class=True)

# name -> (hub register method, C++ enum value, min, max, step)
TYPES = {
    "open_duration": ("register_open_duration", GDONumberType.OPEN_DURATION, 0, 65000, 100),
    "close_duration": ("register_close_duration", GDONumberType.CLOSE_DURATION, 0, 65000, 100),
    "client_id": ("register_client_id", GDONumberType.CLIENT_ID, 0, 0xFFFFFFFF, 1),
    "rolling_code": ("register_rolling_code", GDONumberType.ROLLING_CODE, 0, 0xFFFFFFF, 1),
}

CONFIG_SCHEMA = (
    number.number_schema(GDONumber)
    .extend(
        {
            cv.Required(CONF_TYPE): cv.one_of(*TYPES, lower=True),
        }
    )
    .extend(SECPLUS_GDO_CONFIG_SCHEMA)
)


async def to_code(config):
    register, enum_value, lo, hi, step = TYPES[config[CONF_TYPE]]
    var = await number.new_number(config, min_value=lo, max_value=hi, step=step)
    await cg.register_component(var, config)
    cg.add(var.set_type(enum_value))
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(getattr(hub, register)(var))
