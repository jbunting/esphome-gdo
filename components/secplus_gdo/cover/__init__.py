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
    cg.add(hub.register_door(var))
