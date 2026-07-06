import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import CONF_ID, CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOSensor = secplus_gdo_ns.class_("GDOSensor", sensor.Sensor, cg.Component)

TYPES = {
    "openings": "register_openings",
    "time_to_close": "register_ttc",
}

CONFIG_SCHEMA = (
    sensor.sensor_schema(GDOSensor)
    .extend(
        {
            cv.Required(CONF_TYPE): cv.one_of(*TYPES, lower=True),
        }
    )
    .extend(SECPLUS_GDO_CONFIG_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await sensor.register_sensor(var, config)
    await cg.register_component(var, config)
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    register = TYPES[config[CONF_TYPE]]
    # The entity is a global, so the lambda references it without capturing.
    cg.add(getattr(hub, register)(cg.RawExpression(f"[](float x) {{ {var}->publish_state(x); }}")))
