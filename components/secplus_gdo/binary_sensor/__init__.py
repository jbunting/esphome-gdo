import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import CONF_ID, CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOBinarySensor = secplus_gdo_ns.class_(
    "GDOBinarySensor", binary_sensor.BinarySensor, cg.Component
)

TYPES = {
    "motion": "register_motion",
    "obstruction": "register_obstruction",
    "motor": "register_motor",
    "button": "register_button",
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
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    register = TYPES[config[CONF_TYPE]]
    # The entity is a global, so the lambda references it without capturing.
    cg.add(getattr(hub, register)(cg.RawExpression(f"[](bool x) {{ {var}->publish_state(x); }}")))
