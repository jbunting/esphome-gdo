import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import CONF_ID, CONF_TYPE

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOSensor = secplus_gdo_ns.class_("GDOSensor", sensor.Sensor, cg.Component)
GDOSensorType = secplus_gdo_ns.enum("GDOSensorType", is_class=True)

TYPES = {
    "openings": GDOSensorType.OPENINGS,
    "time_to_close": GDOSensorType.TIME_TO_CLOSE,
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
    cg.add(var.set_type(TYPES[config[CONF_TYPE]]))
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
