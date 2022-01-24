"""Alpha2 tests"""
import pytest

from moehlenhoff_alpha2 import Alpha2Base

HOST = "172.16.1.74"


@pytest.mark.asyncio
async def test_get_heat_areas():
    """Test getting heat areas"""
    base = Alpha2Base(HOST)
    await base.update_data()
    heatareas = list(base.heat_areas)
    assert len(heatareas) > 0


@pytest.mark.asyncio
async def test_update_heatareas():
    """Test updating heat areas"""
    base = Alpha2Base(HOST)
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    t_target = round(heat_area["T_TARGET"] + 0.2, 1)
    await base.update_heat_area(heat_area["ID"], {"T_TARGET": t_target})
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    assert heat_area["T_TARGET"] == t_target
