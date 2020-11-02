# python-moehlenhoff-alpha2
Python client for the Moehlenhoff Alpha2 underfloor heating system

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
    ha = list(base.heatareas)[0]
    t_target = ha["T_TARGET"] + 0.2
    await base.update_heatarea(ha["ID"], {"T_TARGET": t_target})

asyncio.run(main())
```
