"""Test different accessory types: Covers."""
import unittest

from homeassistant.core import callback
from homeassistant.components.cover import (
    ATTR_POSITION, ATTR_CURRENT_POSITION)
from homeassistant.components.homekit.type_covers import (
    WindowCovering, GarageDoorOpener,
    GARAGE_DOOR_OPENER_CLOSED, GARAGE_DOOR_OPENER_OPEN,
    GARAGE_DOOR_OPENER_OPENING)
from homeassistant.const import (
    STATE_UNKNOWN, STATE_OPEN,
    ATTR_SERVICE, ATTR_SERVICE_DATA, ATTR_ASSUMED_STATE,
    EVENT_CALL_SERVICE)

from tests.common import get_test_home_assistant


class TestHomekitSensors(unittest.TestCase):
    """Test class for all accessory types regarding covers."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.events = []

        @callback
        def record_event(event):
            """Track called event."""
            self.events.append(event)

        self.hass.bus.listen(EVENT_CALL_SERVICE, record_event)

    def tearDown(self):
        """Stop down everything that was started."""
        self.hass.stop()

    def test_window_set_cover_position(self):
        """Test if accessory and HA are updated accordingly."""
        window_cover = 'cover.window'

        acc = WindowCovering(self.hass, window_cover, 'Cover', aid=2)
        acc.run()

        self.assertEqual(acc.aid, 2)
        self.assertEqual(acc.category, 14)  # WindowCovering

        self.assertEqual(acc.char_current_position.value, 0)
        self.assertEqual(acc.char_target_position.value, 0)
        self.assertEqual(acc.char_position_state.value, 0)

        self.hass.states.set(window_cover, STATE_UNKNOWN,
                             {ATTR_CURRENT_POSITION: None})
        self.hass.block_till_done()

        self.assertEqual(acc.char_current_position.value, 0)
        self.assertEqual(acc.char_target_position.value, 0)
        self.assertEqual(acc.char_position_state.value, 0)

        self.hass.states.set(window_cover, STATE_OPEN,
                             {ATTR_CURRENT_POSITION: 50})
        self.hass.block_till_done()

        self.assertEqual(acc.char_current_position.value, 50)
        self.assertEqual(acc.char_target_position.value, 50)
        self.assertEqual(acc.char_position_state.value, 2)

        # Set from HomeKit
        acc.char_target_position.client_update_value(25)
        self.hass.block_till_done()
        self.assertEqual(
            self.events[0].data[ATTR_SERVICE], 'set_cover_position')
        self.assertEqual(
            self.events[0].data[ATTR_SERVICE_DATA][ATTR_POSITION], 25)

        self.assertEqual(acc.char_current_position.value, 50)
        self.assertEqual(acc.char_target_position.value, 25)
        self.assertEqual(acc.char_position_state.value, 0)

        # Set from HomeKit
        acc.char_target_position.client_update_value(75)
        self.hass.block_till_done()
        self.assertEqual(
            self.events[0].data[ATTR_SERVICE], 'set_cover_position')
        self.assertEqual(
            self.events[1].data[ATTR_SERVICE_DATA][ATTR_POSITION], 75)

        self.assertEqual(acc.char_current_position.value, 50)
        self.assertEqual(acc.char_target_position.value, 75)
        self.assertEqual(acc.char_position_state.value, 1)

    def test_garage_open(self):
        """Test if accessory and HA are updated accordingly."""
        garage_cover = 'cover.garage'

        acc = GarageDoorOpener(self.hass, garage_cover, 'Cover', aid=2)
        acc.run()

        self.assertEqual(acc.aid, 2)
        self.assertEqual(acc.category, 4)  # GarageDoorOpener

        self.assertEqual(acc.char_current_position.value, GARAGE_DOOR_OPENER_CLOSED)
        self.assertEqual(acc.char_target_position.value, GARAGE_DOOR_OPENER_CLOSED)

        self.hass.states.set(garage_cover, STATE_UNKNOWN,
                             {ATTR_CURRENT_POSITION: None})
        self.hass.block_till_done()

        self.assertEqual(acc.char_current_position.value, GARAGE_DOOR_OPENER_CLOSED)
        self.assertEqual(acc.char_target_position.value, GARAGE_DOOR_OPENER_CLOSED)

        self.hass.states.set(garage_cover, STATE_OPEN, {ATTR_CURRENT_POSITION: 1})
        self.hass.block_till_done()

        self.assertEqual(acc.char_current_position.value, GARAGE_DOOR_OPENER_OPENING)
        self.assertEqual(acc.char_target_position.value, GARAGE_DOOR_OPENER_OPEN)

        # Set from HomeKit (Assumed State is True)
        self.hass.states.set(garage_cover, STATE_UNKNOWN, {ATTR_ASSUMED_STATE: True})

        acc.char_target_position.client_update_value(GARAGE_DOOR_OPENER_OPEN)
        self.hass.block_till_done()
        self.assertEqual(
            self.events[0].data[ATTR_SERVICE], 'open_cover')
        self.assertEqual(acc.char_target_position.value, GARAGE_DOOR_OPENER_CLOSED)

        # Set from HomeKit (Assumed State is False)
        self.hass.states.set(garage_cover, STATE_UNKNOWN, {ATTR_ASSUMED_STATE: False})

        acc.char_target_position.client_update_value(GARAGE_DOOR_OPENER_OPEN)
        self.hass.block_till_done()
        self.assertEqual(
            self.events[0].data[ATTR_SERVICE], 'open_cover')
        self.assertEqual(acc.char_target_position.value, GARAGE_DOOR_OPENER_OPEN)
