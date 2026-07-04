import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import lock
from esphome.const import CONF_ID

from .. import SECPLUS_GDO_CONFIG_SCHEMA, secplus_gdo_ns, CONF_SECPLUS_GDO_ID

DEPENDENCIES = ["secplus_gdo"]

GDOLock = secplus_gdo_ns.class_("GDOLock", lock.Lock, cg.Component)

CONFIG_SCHEMA = lock.lock_schema(GDOLock).extend(SECPLUS_GDO_CONFIG_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await lock.register_lock(var, config)
    hub = await cg.get_variable(config[CONF_SECPLUS_GDO_ID])
    cg.add(hub.register_lock(var))
