"""
Support for Tibber.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.tibber/
"""
import asyncio
from datetime import datetime

import logging

from datetime import timedelta
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

REQUIREMENTS = ['pyTibber==0.2.2']

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_ACCESS_TOKEN): cv.string
})

ICON = 'mdi:currency-usd'
SCAN_INTERVAL = timedelta(minutes=1)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the Tibber sensor."""
    import Tibber
    tibber = Tibber.Tibber(config[CONF_ACCESS_TOKEN],
                           websession=async_get_clientsession(hass))
    yield from tibber.update_info()
    dev = []
    for home in tibber.get_homes():
        yield from home.update_info()
        dev.append(TibberSensor(home))

    async_add_devices(dev)


class TibberSensor(Entity):
    """Representation of an Tibber sensor."""

    def __init__(self, tibber_home):
        """Initialize the sensor."""
        self._tibber_home = tibber_home
        self._last_updated = None
        self._state = None
        self._device_state_attributes = {}
        self._unit_of_measurement = None
        self._name = 'Electricity price {}'.format(self._tibber_home.address1)

    @asyncio.coroutine
    def async_update(self):
        """Get the latest data and updates the states."""
        if self._tibber_home.current_price_total and self._last_updated and \
           dt_util.as_utc(dt_util.parse_datetime(self._last_updated)).hour\
           == dt_util.utcnow().hour:
            return

        yield from self._tibber_home.update_price_info()

        self._state = self._tibber_home.current_price_total
        if not self._state:
            _LOGGER.error('No data from Tibber. Check your network connection')
            return
        data = []
        future = False
        prev_y = None
        prev_date = None
        for x_val, y_val in sorted(self._tibber_home.price_total.items()):
            _date = datetime.strptime(''.join(x_val.rsplit(':', 1)),
                                      '%Y-%m-%dT%H:%M:%S%z')
            if _date > dt_util.utcnow() and not future:
                future = True
                _data = [{'x': prev_date.isoformat(), 'y': [None, prev_y, None]},
                         {'x': _date.isoformat(), 'y': [None, y_val, None]}]
                data += _d
            if not future:
                _data = [{'x': _date.isoformat(), 'y': [y_val, None, None]}]
            else:
                _data = [{'x': _date.isoformat(), 'y': [None, None, y_val]}]
            data += _data
            prev_y = y_val
            prev_date = _date
        self._device_state_attributes = self._tibber_home.current_price_info
        _plot_data = {'data': data,
                      'color': ['#666666', 'red', 'blue'],
                      'attr': ['Electricity price',
                               'Electricity price',
                               'Electricity price']}
        self._device_state_attributes['_plot_data'] = _plot_data

        self._last_updated = self._tibber_home.current_price_info.\
            get('startsAt')
        self._unit_of_measurement = self._tibber_home.price_unit

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return self._unit_of_measurement
