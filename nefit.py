"""
Support for Bosch home thermostats.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/xxxxxx/
"""

REQUIREMENTS = ['aionefit==0.3']

import asyncio
import concurrent
from datetime import timedelta
import homeassistant.helpers.config_validation as cv
from homeassistant.exceptions import PlatformNotReady, InvalidStateError
import logging
import voluptuous as vol

from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA,
    STATE_AUTO, STATE_MANUAL, 
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_OPERATION_MODE)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.const import STATE_UNKNOWN, EVENT_HOMEASSISTANT_STOP

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE)

OPERATION_MANUAL = "manual"
OPERATION_AUTO = "auto"

CONF_NAME = "name"
CONF_SERIAL = "serial"
CONF_ACCESSKEY = "accesskey"
CONF_PASSWORD = "password"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_SERIAL): cv.string,
    vol.Required(CONF_ACCESSKEY): cv.string,
    vol.Required(CONF_PASSWORD): cv.string
})

async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):

    name = config.get(CONF_NAME)
    serial = config.get(CONF_SERIAL)
    accesskey = config.get(CONF_ACCESSKEY)
    password = config.get(CONF_PASSWORD)

    _LOGGER.debug("Creating device")
    device = NefitThermostat(hass, name, serial, accesskey, password)
    await device.connect()
    async_add_entities([device], True)
    _LOGGER.debug("async_setup_platform done")

class NefitThermostat(ClimateDevice):
    """Representation of a NefitThermostat device."""

    def __init__(self, hass, name, serial, accesskey, password):
        from aionefit import NefitCore
        """Initialize the thermostat."""
        self.hass = hass
        self._name = name

        self.error_state = "initializing"
        self._online = False
        self._unit_of_measurement = TEMP_CELSIUS
        self._uistatus = None
        self._attributes = {}
        self._stateattr = {}
        self._data = {}
        self._operation_list = [OPERATION_MANUAL, OPERATION_AUTO]

        self._client = NefitCore(serial_number=serial,
                       access_key=accesskey,
                       password=password,
                       message_callback=self.parse_message)
        self._client.failed_auth_handler=self.failed_auth_handler

    async def connect(self):
        self._client.connect()
        _LOGGER.debug("Waiting for connected event")        
        try:
            # await self._client.xmppclient.connected_event.wait()
            await asyncio.wait_for(self._client.xmppclient.connected_event.wait(), timeout=5.0)
            _LOGGER.debug("adding stop listener")
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP,
                                            self._shutdown)
        except concurrent.futures._base.TimeoutError:
            _LOGGER.debug("TimeoutError on waiting for connected event")
            self.hass.components.persistent_notification.create( 
                'Timeout while connecting to Bosch cloud. Retrying in the background',
                title='Nefit error',
                notification_id='nefit_logon_error')
            raise PlatformNotReady
        
        if self.error_state == "authentication_failed":
            self.hass.components.persistent_notification.create( 
                'Invalid credentials while connecting to Bosch cloud.',
                title='Nefit error',
                notification_id='nefit_logon_error')
            raise PlatformNotReady

    def failed_auth_handler(self, event):
        self.error_state = "authentication_failed"
        self._client.xmppclient.connected_event.set()

    @property
    def supported_features(self):
        """Return the list of supported features.
        """
        return SUPPORT_FLAGS

    @property
    def target_temperature_step(self):
        return 0.5

    def parse_message(self, data):
        """Message received callback function for the XMPP client.
        """
        _LOGGER.debug("parse_message callback called with data %s", data)
        if not 'id' in data:
            _LOGGER.error("Unknown response received: %s", data)
            return

        if data['id'] == '/ecus/rrc/uiStatus':
            self._uistatus = data['value']
            self._data['temp_setpoint'] = float(data['value']['TSP'])
            self._data['inhouse_temperature'] = float(data['value']['IHT'])
            self._data['user_mode'] = data['value']['UMD']
            self._stateattr['current_time'] = data['value']['CTD']        
        elif data['id'] == '/heatingCircuits/hc1/actualSupplyTemperature':
            self._stateattr['supply_temperature'] = data['value']
        elif data['id'] == '/system/sensors/temperatures/outdoor_t1':
            self._stateattr['outdoor_temperature'] = data['value']
        elif data['id'] == '/system/appliance/systemPressure':
            self._stateattr['system_pressure'] = data['value']            
        elif data['id'] == '/ecus/rrc/recordings/yearTotal':
            self._stateattr['year_total'] = data['value']
            
    async def async_update(self):
        """Get latest data
        """
        _LOGGER.debug("async_update called")
        self._client.get('/ecus/rrc/uiStatus')
        self._client.get('/heatingCircuits/hc1/actualSupplyTemperature')
        self._client.get('/system/sensors/temperatures/outdoor_t1')
        self._client.get('/system/appliance/systemPressure')
        self._client.get('/ecus/rrc/recordings/yearTotal')

        await asyncio.wait_for(self._client.xmppclient.message_event.wait(), timeout=10.0)
        self._client.xmppclient.message_event.clear()
        _LOGGER.debug("async_update finished")

    @property
    def name(self):
        """Return the name of the ClimateDevice.
        """
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement.
        """
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature.
        """
        if 'inhouse_temperature' in self._data:
            return self._data.get('inhouse_temperature')
        else:
            return 0

    @property
    def target_temperature(self):
        if 'temp_setpoint' in self._data:
            return self._data.get('temp_setpoint')
        else:
            return 0

    @property
    def operation_list(self):
        """List of available operation modes."""
        return [STATE_AUTO, STATE_MANUAL]

    @property
    def current_operation(self):
        if self._data.get('user_mode') == 'manual':
            return OPERATION_MANUAL
        elif self._data.get('user_mode') == 'clock':
            return OPERATION_AUTO
        else:
            return STATE_UNKNOWN

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""

        return self._stateattr

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        _LOGGER.debug("set_operation_mode called mode={}.".format(operation_mode))
        if operation_mode == "manual":
            new_mode = "manual"
        else:
            new_mode = "clock"

        self._client.set_usermode(new_mode)
        await asyncio.wait_for(self._client.xmppclient.message_event.wait(), timeout=10.0)
        self._client.xmppclient.message_event.clear()
        self._data['user_mode'] = new_mode

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug("set_temperature called (temperature={}).".format(temperature))
        self._client.set_temperature(temperature)
        await asyncio.wait_for(self._client.xmppclient.message_event.wait(), timeout=10.0)
        self._client.xmppclient.message_event.clear()
        self._data['target_temperature'] = temperature
        

    def _shutdown(self, event):
        _LOGGER.debug("shutdown")
        self._client.disconnect()
