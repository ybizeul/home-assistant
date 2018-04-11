"""Class to hold all cover accessories."""
import logging

from homeassistant.components.cover import ATTR_CURRENT_POSITION
from homeassistant.const import ATTR_ASSUMED_STATE

from . import TYPES
from .accessories import HomeAccessory, add_preload_service, setup_char
from .const import (
    CATEGORY_WINDOW_COVERING, SERV_WINDOW_COVERING,
    CATEGORY_GARAGE_DOOR_OPENER, SERV_GARAGE_DOOR_OPENER,
    CHAR_CURRENT_POSITION, CHAR_TARGET_POSITION, CHAR_POSITION_STATE,
    CHAR_CURRENT_DOOR_STATE, CHAR_TARGET_DOOR_STATE)
<<<<<<< HEAD
=======

>>>>>>> 1999dbf52f5fa4b8c534747cb27055d60bf0c79d

_LOGGER = logging.getLogger(__name__)


@TYPES.register('WindowCovering')
class WindowCovering(HomeAccessory):
    """Generate a Window accessory for a cover entity.

    The cover entity must support: set_cover_position.
    """

    def __init__(self, *args, config):
        """Initialize a WindowCovering accessory object."""
        super().__init__(*args, category=CATEGORY_WINDOW_COVERING)

        self.current_position = None
        self.homekit_target = None

        serv_cover = add_preload_service(self, SERV_WINDOW_COVERING)
        self.char_current_position = setup_char(
            CHAR_CURRENT_POSITION, serv_cover, value=0)
        self.char_target_position = setup_char(
            CHAR_TARGET_POSITION, serv_cover, value=0,
            callback=self.move_cover)
        self.char_position_state = setup_char(
            CHAR_POSITION_STATE, serv_cover, value=0)

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

    def update_state(self, new_state):
        """Update cover position after state changed."""
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

    The cover entity must have device class 'garage'
    If 'assume_state' property is also set on the entity then 'Closed'
    state will immediatly be sent to homekit after opening
    If the entity reports position, it'll be used to send 'Opening' and
    'Closing' status to HomeKit.
    """

    def __init__(self, hass, entity_id, display_name, **kwargs):
        """Initialize a GarageDoorOpener accessory object."""
        super().__init__(*args, category=CATEGORY_GARAGE_DOOR_OPENER)

        self.hass = hass
        self.entity_id = entity_id
        self.current_state = GARAGE_DOOR_OPENER_CLOSED

        serv_cover = add_preload_service(self, SERV_GARAGE_DOOR_OPENER)

        self.char_current_position = setup_char(
            CHAR_CURRENT_DOOR_STATE, serv_cover, value=GARAGE_DOOR_OPENER_CLOSED)
        self.char_target_position = setup_char(
            CHAR_TARGET_DOOR_STATE, serv_cover, value=GARAGE_DOOR_OPENER_CLOSED,
            callback=self.open_or_close)
        
    def open_or_close(self, value):
        """Open or close door if call came from HomeKit."""
        if value != self.current_state:
            _LOGGER.debug('%s: Set state to %d', self.entity_id, value)

            assumed_state = self.hass.states.get(self.entity_id).attributes.get(ATTR_ASSUMED_STATE)

            if value == GARAGE_DOOR_OPENER_OPEN:
                self.hass.components.cover.open_cover(self.entity_id)

                if assumed_state:
                    self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)
                    self.current_state = GARAGE_DOOR_OPENER_CLOSED
                else:
                    self.char_target_position.set_value(GARAGE_DOOR_OPENER_OPEN)
                    self.char_current_position.set_value(GARAGE_DOOR_OPENER_OPENING)
                    self.current_state = GARAGE_DOOR_OPENER_OPENING

            elif value == GARAGE_DOOR_OPENER_CLOSED:
                self.hass.components.cover.close_cover(self.entity_id)

                self.char_target_position.set_value(GARAGE_DOOR_OPENER_CLOSED)

    def update_state(self, entity_id=None, old_state=None, new_state=None):
        """Update cover position after state changed."""

        if new_state is None:
            return

        old_position = None

        if old_state:
            old_position = old_state.attributes.get(ATTR_CURRENT_POSITION)

        if old_position == None:
            old_position = 0

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
        elif new_position >= old_position:
            self.char_target_position.set_value(GARAGE_DOOR_OPENER_OPEN)
            current_state = GARAGE_DOOR_OPENER_OPENING

        self.current_state = current_state

        if isinstance(current_state, int):
            self.char_current_position.set_value(current_state)
