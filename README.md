# ha-nefit
Home Assistant Nefit climate component

## Installation

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