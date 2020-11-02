import pytest
from moehlenhoff_alpha2 import __version__, Alpha2Base

HOST = "172.16.1.74"

def test_version():
    assert __version__ == '1.0'

@pytest.mark.asyncio
async def test_get_heatareas():
    base = Alpha2Base(HOST)
    await base.update_data()
    heatareas = list(base.heatareas)
    assert len(heatareas) > 0

@pytest.mark.asyncio
async def test_update_heatareas():
    base = Alpha2Base(HOST)
    await base.update_data()
    ha = list(base.heatareas)[0]
    t_target = ha["T_TARGET"] + 0.2
    await base.update_heatarea(ha["ID"], {"T_TARGET": t_target})
    await base.update_data()
    ha = list(base.heatareas)[0]
    assert ha["T_TARGET"] == t_target


