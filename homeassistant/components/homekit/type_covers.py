"""Class to hold all cover accessories."""
import logging

from homeassistant.components.cover import ATTR_CURRENT_POSITION
from homeassistant.const import ATTR_ASSUMED_STATE,STATE_UNKNOWN

from . import TYPES
from .accessories import HomeAccessory, add_preload_service
from .const import (
    CATEGORY_WINDOW_COVERING, SERV_WINDOW_COVERING,
    CATEGORY_GARAGE_DOOR_OPENER, SERV_GARAGE_DOOR_OPENER,
    CHAR_CURRENT_POSITION, CHAR_TARGET_POSITION, CHAR_POSITION_STATE,
    CHAR_CURRENT_DOOR_STATE,CHAR_TARGET_DOOR_STATE)


_LOGGER = logging.getLogger(__name__)


@TYPES.register('WindowCovering')
class WindowCovering(HomeAccessory):
    """Generate a Window accessory for a cover entity.

    The cover entity must support: set_cover_position.
    """

    def __init__(self, hass, entity_id, display_name, **kwargs):
        """Initialize a WindowCovering accessory object."""
        super().__init__(display_name, entity_id,
                         CATEGORY_WINDOW_COVERING, **kwargs)

        self.hass = hass
        self.entity_id = entity_id
        
        self.current_position = None
        self.homekit_target = None

        serv_cover = add_preload_service(self, SERV_WINDOW_COVERING)
        self.char_current_position = serv_cover. \
            get_characteristic(CHAR_CURRENT_POSITION)
        self.char_target_position = serv_cover. \
            get_characteristic(CHAR_TARGET_POSITION)
        self.char_position_state = serv_cover. \
            get_characteristic(CHAR_POSITION_STATE)
        self.char_current_position.value = 0
        self.char_target_position.value = 0
        self.char_position_state.value = 0

        self.char_target_position.setter_callback = self.move_cover

    def move_cover(self, value):
        """Move cover to value if call came from HomeKit."""
        if value != self.current_position:
            _LOGGER.debug('%s: Set position to %d', self.entity_id, value)
            self.homekit_target = value
            if value > self.current_position:
                self.char_position_state.set_value(1)
            elif value < self.current_position:
                self.char_position_state.set_value(0)
            self.hass.components.cover.set_cover_position(
                value, self.entity_id)

    def update_state(self, entity_id=None, old_state=None, new_state=None):
        """Update cover position after state changed."""
        if new_state is None:
            return

        current_position = new_state.attributes.get(ATTR_CURRENT_POSITION)
        if isinstance(current_position, int):
            self.current_position = current_position
            self.char_current_position.set_value(self.current_position)
            if self.homekit_target is None or \
                    abs(self.current_position - self.homekit_target) < 6:
                self.char_target_position.set_value(self.current_position)
                self.char_position_state.set_value(2)
                self.homekit_target = None

GARAGE_DOOR_OPENER_CLOSED = int(1)
GARAGE_DOOR_OPENER_CLOSING = int(3)
GARAGE_DOOR_OPENER_OPEN = int(0)
GARAGE_DOOR_OPENER_OPENING = int(2)
GARAGE_DOOR_OPENER_STOPPED = int(4)

@TYPES.register('GarageDoorOpener')
class GarageDoorOpener(HomeAccessory):
    """Generate a GarageDoorOpener accessory for a cover entity.
    """

    def __init__(self, hass, entity_id, display_name, **kwargs):
        """Initialize a GarageDoorOpener accessory object."""
        super().__init__(display_name, entity_id,
            CATEGORY_GARAGE_DOOR_OPENER, **kwargs)

        self.hass = hass
        self.entity_id = entity_id
        self.current_state = GARAGE_DOOR_OPENER_CLOSED

        serv_cover = add_preload_service(self, SERV_GARAGE_DOOR_OPENER)

        self.char_current_position = serv_cover. \
            get_characteristic(CHAR_CURRENT_DOOR_STATE)
        self.char_target_position = serv_cover. \
            get_characteristic(CHAR_TARGET_DOOR_STATE)

        self.char_current_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
        self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
        
        self.char_target_position.setter_callback = self.open_or_close

    def open_or_close(self, value):
        """Open or close door if call came from HomeKit."""
        if value != self.current_state:
            _LOGGER.debug('%s: Set state to %d', self.entity_id, value)

            """ If assumed_state is true, we need to assume the door is closed right away """
            assumed_state = self.hass.states.get(self.entity_id).attributes.get(ATTR_ASSUMED_STATE)

            if value is GARAGE_DOOR_OPENER_OPEN:
                """Desired state sent by HomeKit is Open"""

                self.hass.components.cover.open_cover(self.entity_id)

                if assumed_state:
                    self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
                    self.current_state = GARAGE_DOOR_OPENER_CLOSED
                else:
                    self.char_target_position.set_value(GARAGE_DOOR_OPENER_OPEN)
                    self.current_state = GARAGE_DOOR_OPENER_OPEN


            elif value is GARAGE_DOOR_OPENER_CLOSED:
                """Desired state sent by HomeKit is Closed"""
                self.hass.components.cover.close_cover(self.entity_id)

                self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
                #self.hass.components.cover.set_cover_position(0, self.entity_id)
            

    def update_state(self, entity_id=None, old_state=None, new_state=None):
        """Update cover position after state changed."""

        if new_state is None:
            return
        
        _LOGGER.debug('%s: New state %s', self.entity_id, str(new_state))

        old_position = None
        
        if old_state:
            old_position = old_state.attributes.get(ATTR_CURRENT_POSITION)

        new_position = new_state.attributes.get(ATTR_CURRENT_POSITION)

        if new_position is None:
            return

        if new_position is 0:
            self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
            current_state = GARAGE_DOOR_OPENER_CLOSED
        elif new_position is 100:
            current_state = GARAGE_DOOR_OPENER_OPEN
            self.char_target_position.set_value(GARAGE_DOOR_OPENER_OPEN)
        elif new_position < old_position:
            self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
            current_state = GARAGE_DOOR_OPENER_CLOSING
        elif new_position >=  old_position:
            self.char_target_position.set_value(GARAGE_DOOR_OPENER_OPEN)
            current_state = GARAGE_DOOR_OPENER_OPENING

        self.current_state = current_state

        if isinstance(current_state, int):
            self.char_current_position.set_value(current_state)
