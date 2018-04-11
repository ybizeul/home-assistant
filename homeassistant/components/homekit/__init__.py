"""Support for Apple HomeKit.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/homekit/
"""
import logging
from zlib import adler32

import voluptuous as vol

from homeassistant.components.cover import SUPPORT_SET_POSITION
from homeassistant.const import (
    ATTR_SUPPORTED_FEATURES,ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT,
    CONF_PORT, TEMP_CELSIUS, TEMP_FAHRENHEIT,
    EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entityfilter import FILTER_SCHEMA
from homeassistant.util import get_local_ip
from homeassistant.util.decorator import Registry
from .const import (
    DOMAIN, HOMEKIT_FILE, CONF_AUTO_START, CONF_ENTITY_CONFIG, CONF_FILTER,
    DEFAULT_PORT, DEFAULT_AUTO_START, SERVICE_HOMEKIT_START)
from .util import (
    validate_entity_config, show_setup_message)

TYPES = Registry()
_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['HAP-python==1.1.9']


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.All({
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_AUTO_START, default=DEFAULT_AUTO_START): cv.boolean,
        vol.Optional(CONF_FILTER, default={}): FILTER_SCHEMA,
        vol.Optional(CONF_ENTITY_CONFIG, default={}): validate_entity_config,
    })
}, extra=vol.ALLOW_EXTRA)


async def async_setup(hass, config):
    """Setup the HomeKit component."""
    _LOGGER.debug('Begin setup HomeKit')

    conf = config[DOMAIN]
    port = conf[CONF_PORT]
    auto_start = conf[CONF_AUTO_START]
    entity_filter = conf[CONF_FILTER]
    entity_config = conf[CONF_ENTITY_CONFIG]

    homekit = HomeKit(hass, port, entity_filter, entity_config)
    homekit.setup()

    if auto_start:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, homekit.start)
        return True

    def handle_homekit_service_start(service):
        """Handle start HomeKit service call."""
        if homekit.started:
            _LOGGER.warning('HomeKit is already running')
            return
        homekit.start()

    hass.services.async_register(DOMAIN, SERVICE_HOMEKIT_START,
                                 handle_homekit_service_start)

    return True


def get_accessory(hass, state, aid, config):
    """Take state and return an accessory object if supported."""
    if not aid:
        _LOGGER.warning('The entitiy "%s" is not supported, since it '
                        'generates an invalid aid, please change it.',
                        state.entity_id)
        return None

    a_type = None
    config = config or {}

    if state.domain == 'alarm_control_panel':
        a_type = 'SecuritySystem'

    elif state.domain == 'binary_sensor' or state.domain == 'device_tracker':
        a_type = 'BinarySensor'

    elif state.domain == 'climate':
        a_type = 'Thermostat'

    elif state.domain == 'cover':
        # Only add covers that support set_cover_position or garage doors

        features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
        isGarageDoor = state.attributes.get(ATTR_DEVICE_CLASS) == 'garage'

        if isGarageDoor:
            a_type = 'GarageDoorOpener'

        elif features & SUPPORT_SET_POSITION:
            a_type = 'WindowCovering'

    elif state.domain == 'light':
        a_type = 'Light'
    
    elif state.domain == 'lock':
        a_type = 'Lock'

    elif state.domain == 'sensor':
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if unit == TEMP_CELSIUS or unit == TEMP_FAHRENHEIT:
            a_type = 'TemperatureSensor'
        elif unit == '%':
            a_type = 'HumiditySensor'

    elif state.domain == 'switch' or state.domain == 'remote' \
            or state.domain == 'input_boolean' or state.domain == 'script':
        a_type = 'Switch'

    if a_type is None:
        return None

    _LOGGER.debug('Add "%s" as "%s"', state.entity_id, a_type)

    return TYPES[a_type](hass, state.name, state.entity_id, aid, config=config)


def generate_aid(entity_id):
    """Generate accessory aid with zlib adler32."""
    aid = adler32(entity_id.encode('utf-8'))
    if aid == 0 or aid == 1:
        return None
    return aid


class HomeKit():
    """Class to handle all actions between HomeKit and Home Assistant."""

    def __init__(self, hass, port, entity_filter, entity_config):
        """Initialize a HomeKit object."""
        self.hass = hass
        self._port = port
        self._filter = entity_filter
        self._config = entity_config
        self.started = False

        self.bridge = None
        self.driver = None

    def setup(self):
        """Setup bridge and accessory driver."""
        from .accessories import HomeBridge, HomeDriver

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self.stop)

        path = self.hass.config.path(HOMEKIT_FILE)
        self.bridge = HomeBridge(self.hass)
        self.driver = HomeDriver(self.bridge, self._port, get_local_ip(), path)

    def add_bridge_accessory(self, state):
        """Try adding accessory to bridge if configured beforehand."""
        if not state or not self._filter(state.entity_id):
            return
        aid = generate_aid(state.entity_id)
        conf = self._config.pop(state.entity_id, {})
        acc = get_accessory(self.hass, state, aid, conf)
        if acc is not None:
            self.bridge.add_accessory(acc)

    def start(self, *args):
        """Start the accessory driver."""
        if self.started:
            return
        self.started = True

        # pylint: disable=unused-variable
        from . import (  # noqa F401
            type_covers, type_lights, type_locks, type_security_systems,
            type_sensors, type_switches, type_thermostats)

        for state in self.hass.states.all():
            self.add_bridge_accessory(state)
        self.bridge.set_broker(self.driver)

        if not self.bridge.paired:
            show_setup_message(self.hass, self.bridge)

        _LOGGER.debug('Driver start')
        self.driver.start()

    def stop(self, *args):
        """Stop the accessory driver."""
        if not self.started:
            return

        _LOGGER.debug('Driver stop')
        if self.driver and self.driver.run_sentinel:
            self.driver.stop()
