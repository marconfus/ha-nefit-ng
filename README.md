For a more up to date version see here: https://github.com/ksya/ha-nefiteasy



# ha-nefit
Home Assistant Nefit climate component

## Installation

Create ```custom_components/nefit/``` in your homeassistant config directory and copy the file [```nefit.py```](https://raw.githubusercontent.com/marconfus/ha-nefit-ng/master/nefit.py) into it with the filename ```climate.py``` also create an empty file with the name ```__init__.py``` into the same folder..


BEFORE Home Assistant version **0.88**:

Create ```custom_components/climate/``` in your homeassistant config directory and copy the file [```nefit.py```](https://raw.githubusercontent.com/marconfus/ha-nefit-ng/master/nefit.py) into it.

Please ignore all instructions about manually installing python packages as they are outdated!

## Configuration

```
climate:
  platform: nefit
  name: Heating
  serial: 'XXXXXXXXX'
  accesskey: 'xxxxxxxxx'
  password: 'xxxxxxxxx'
```

If any of your secrets in the configuration is numbers only, make sure to put it between quotes (`'`) to have homeassistant parse them correctly.

## Sensors

More information from the thermostat is saved in state attributes. If you want that data as a sensor you can do that easily with the template platform:

```
sensor:
  - platform: template
    sensors:
      outdoor_temperature:
        friendly_name: 'Outdoor temperature'
        unit_of_measurement: '°C'
        value_template: "{{ state_attr('climate.heating', 'outdoor_temperature') }}"
      gas_year_total:
        friendly_name: 'Gas year total'
        unit_of_measurement: 'kWh'
        value_template: "{{ state_attr('climate.heating', 'year_total') }}"
```
To see what state attributes are available open "States" in the Home Assistant Developer tools.

## Debugging problems

```
logger:
  default: info
  logs:
    custom_components.climate.nefit: debug
    aionefit: debug
```
