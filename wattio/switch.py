""" Platform for Wattio integration testing """
import logging

""" Custom imports """
from . import (
	wattioAPI,WattioRegisterView,check_config_file,get_auth_uri,request_app_setup,request_oauth_completion,
	ATTR_ACCESS_TOKEN, ATTR_CLIENT_ID, ATTR_LAST_SAVED_AT,WATTIO_CONF_FILE,	WATTIO_AUTH_CALLBACK_PATH,
	WATTIO_AUTH_START,WATTIO_AUTH_URI,WATTIO_TOKEN_URI,DEFAULT_CONFIG,configuring
)

""" HASSIO imports """
from homeassistant.util.json import load_json, save_json
from homeassistant.helpers.entity import Entity
from homeassistant.const import TEMP_CELSIUS
from homeassistant.const import (CONF_SCAN_INTERVAL)
from homeassistant.components.light import Light

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, add_entities, discovery_info=None):
	""" Wattio Sensor setup platform """
	_LOGGER.debug("Wattio Switch component running ...")
	config_path = hass.config.path(WATTIO_CONF_FILE)
	_LOGGER.debug("Wattio config file: %s" %(config_path))
	config_status = check_config_file(config_path)
	""" Check Wattio file configuration status """
	if config_status == 2:
		request_app_setup(hass, config, add_devices,add_entities, config_path, setup_platform, discovery_info=None)
		return False
	elif config_status ==1:
		_LOGGER.error("Config file doesn't exist, creating ...")
		save_json(config_path, DEFAULT_CONFIG)
		request_app_setup( hass, config, add_devices,add_entities, config_path, setup_platform, discovery_info=None)
		return False
	if "wattio" in configuring:
        	hass.components.configurator.request_done(configuring.pop("wattio"))

	config_file = load_json(config_path)
	token = config_file.get(ATTR_ACCESS_TOKEN)
	""" 
	Wattio Token does not expire 
	expires_at = config_file.get(ATTR_LAST_SAVED_AT)
	"""
	if token is not None:
		apidata = wattioAPI(config.get(CONF_SCAN_INTERVAL),token)
		registered_devices = apidata.get_devices()
		dev = []
		""" Create Updater Object """
		for device in registered_devices:
			measurement = None
			icon = None
			if device["type"] == "pod":
				add_devices([WattioSwitch(device["name"],device["type"],measurement,icon,apidata,device["ieee"])], True)
				_LOGGER.debug("Adding device: %s" %(device["name"]))	
	else:
		''' Not Authorized, need to complete OAUTH2 process '''
		auth_uri = get_auth_uri(hass,config_file.get("client_id"))
		_LOGGER.error("No token configured, complete OAUTH2 authorization: %s" %(auth_uri))
		hass.http.register_view(WattioRegisterView(hass,config,add_entities,config_file.get("client_id"),config_file.get("client_secret"),auth_uri))
		request_oauth_completion(hass,config,add_devices,add_entities,auth_uri,setup_platform)



class WattioSwitch(Light):
	""" Representation of Sensor """
	def __init__(self, name, devtype, measurement,icon,apidata,ieee,channel=None):
		"""Initialize the sensor."""
		self._name = name
		self._is_on = None
		self._state = None
		self._icon = icon
		self._apidata = apidata
		self._ieee = ieee
		self._devtype = devtype
		self._channel = None
		self._current_consumption = None
		#self.type = resource_type
		if self._state == None:
			self.update()

	@property
	def is_on(self):
		return self._state
	
	def turn_on(self):
		self._state = 1
		_LOGGER.error("Encendiendo")
		return self._apidata.set_switch_status(self._ieee,"on")
	
	def turn_off(self):
		self._state = 0
		_LOGGER.error("Apagando")		
		return self._apidata.set_switch_status(self._ieee,"off")

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def available(self):
		availability = self._apidata.get_device_availability(self._ieee)
		return availability

	def update(self):
		switchvalue = self._apidata.update_switch_status(self._name,self._devtype,self._ieee)
		_LOGGER.error("%s - %s" %(self._name,switchvalue))
		self._state = switchvalue
		return self._state