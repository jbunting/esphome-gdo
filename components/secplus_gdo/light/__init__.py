import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import light
from esphome.const import CONF_OUTPUT_ID

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOLight = secplus_gdo_ns.class_("GDOLight", light.LightOutput, cg.Component)

CONFIG_SCHEMA = light.light_schema(GDOLight, light.LightType.BINARY).extend(
    SECPLUS_GDO_CONFIG_SCHEMA
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_OUTPUT_ID])
    await cg.register_component(var, config)
    await light.register_light(var, config)
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(hub.add_handle_listener(cg.RawExpression(f"[](gdo_handle_t h) {{ {var}->set_gdo_handle(h); }}")))
    cg.add(
        hub.add_event_listener(
            cg.RawExpression(f"[](const gdo_status_t *s, gdo_cb_event_t e) {{ {var}->on_gdo_event(s, e); }}")
        )
    )
