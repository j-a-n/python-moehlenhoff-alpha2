# python-moehlenhoff-alpha2
Python client for the Moehlenhoff Alpha2 underfloor heating system

## Vendor documentation
- https://www.ezr-portal.de/backend/documents.php?d=Alpha2_XML_Schnittstellen_Informationen.zip

## Installation

Moehlenhoff Alpha2 can be installed from PyPI using `pip` or your package manager of choice:

``` bash
pip install moehlenhoff-alpha2
```

## Usage example

``` python
import asyncio
from moehlenhoff_alpha2 import Alpha2Base

async def main():
    base = Alpha2Base("192.168.1.1")
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    t_target = heat_area["T_TARGET"] + 0.2
    await base.update_heat_area(heat_area["ID"], {"T_TARGET": t_target})

asyncio.run(main())
```
