"""Alpha2 tests"""

import asyncio
import os
from datetime import datetime
from unittest.mock import patch

import pytest

from moehlenhoff_alpha2 import Alpha2Base

ALPHA2_BASE_ADDRESS = os.environ.get("ALPHA2_BASE_ADDRESS")


@pytest.mark.parametrize(
    "host, expected_base_url",
    (
        ("alpha2", "http://alpha2"),
        ("192.168.1.11", "http://192.168.1.11"),
        ("http://192.168.1.11/", "http://192.168.1.11"),
        ("http://alpha2.lan", "http://alpha2.lan"),
        ("https://alpha2.lan", "http://alpha2.lan"),
    ),
)
def test_init_host_argument(host: str, expected_base_url: str) -> None:
    """Test type conversion from xml"""
    assert Alpha2Base(host).base_url == expected_base_url


@pytest.mark.parametrize(
    "entity_type, attribute, value, expected_value",
    (
        ("HEATAREA", "BLOCK_HC", "1", True),
        ("HEATAREA", "BLOCK_HC", "0", False),
        ("HEATAREA", "HEATAREA_NAME", "1.1", "1.1"),
        ("HEATAREA", "HEATAREA_MODE", "1", 1),
        ("HEATAREA", "T_ACTUAL", "19.2", 19.2),
        ("IODEVICE", "BATTERY", "2", 2),
        ("HEATCTRL", "INUSE", "0", False),
    ),
)
def test_convert_types_from_xml(entity_type: str, attribute: str, value: str, expected_value: bool | float | int) -> None:
    """Test type conversion from xml"""
    result = Alpha2Base.convert_types_from_xml(entity_type, {attribute: value})[attribute]
    assert isinstance(result, type(expected_value))
    assert result == expected_value


def test_convert_types_from_xml_error() -> None:
    """Test type conversion from xml error"""
    with pytest.raises(ValueError):
        Alpha2Base.convert_types_from_xml("INVALID", {})


@pytest.mark.parametrize(
    "entity_type, attribute, value, expected_value",
    (
        ("HEATAREA", "BLOCK_HC", True, "1"),
        ("HEATAREA", "BLOCK_HC", False, "0"),
        ("HEATAREA", "HEATAREA_NAME", "2", "2"),
        ("HEATAREA", "HEATAREA_MODE", 1, "1"),
        ("HEATAREA", "T_ACTUAL", 19.2122312, "19.2"),
    ),
)
def test_convert_types_for_xml(entity_type: str, attribute: str, value: bool | str | int | float, expected_value: str) -> None:
    """Test type conversion for xml"""
    result = Alpha2Base.convert_types_for_xml(entity_type, {attribute: value})[attribute]
    assert isinstance(result, type(expected_value))
    assert result == expected_value


def test_convert_types_for_xml_error() -> None:
    """Test type conversion for xml error"""
    with pytest.raises(ValueError):
        Alpha2Base.convert_types_for_xml("INVALID", {})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "xml_file, base_id, base_name, num_heat_areas, num_heat_controls, num_io_devices",
    (("static1.xml", "EZR012345", "EZR012345", 6, 12, 6), ("static2.xml", "Alpha2Test", "Alpha2Test", 1, 12, 1)),
)
async def test_parse_xml(
    xml_file: str, base_id: str, base_name: str, num_heat_areas: int, num_heat_controls: int, num_io_devices: int
) -> None:
    """Test xml parsing"""

    async def _fetch_static_data(_self: Alpha2Base) -> str:
        with open(os.path.join("tests/data", xml_file), "r", encoding="utf-8") as file:
            return file.read()

    with patch("moehlenhoff_alpha2.Alpha2Base._fetch_static_data", _fetch_static_data):
        base = Alpha2Base("127.0.0.1")
        await base.update_data()
        assert base.id == base_id
        assert base.name == base_name

        assert len(list(base.heat_areas)) == num_heat_areas
        assert len(list(base.heat_controls)) == num_heat_controls
        assert len(list(base.io_devices)) == num_io_devices


@pytest.mark.asyncio
async def test_heatarea_ids() -> None:
    """Test _HEATAREA_ID attribute"""

    async def _fetch_static_data(_self: Alpha2Base) -> str:
        with open(os.path.join("tests/data/static1.xml"), "r", encoding="utf-8") as file:
            return file.read()

    with patch("moehlenhoff_alpha2.Alpha2Base._fetch_static_data", _fetch_static_data):
        base = Alpha2Base("127.0.0.1")
        await base.update_data()

        heat_controls = {hc["NR"]: hc for hc in base.heat_controls}
        assert heat_controls[1]["_HEATAREA_ID"] == "EZR012345:1"
        assert heat_controls[2]["_HEATAREA_ID"] == "EZR012345:1"
        assert heat_controls[3]["_HEATAREA_ID"] == "EZR012345:1"
        assert heat_controls[4]["_HEATAREA_ID"] == "EZR012345:4"
        assert heat_controls[5]["_HEATAREA_ID"] == "EZR012345:5"
        assert heat_controls[6]["_HEATAREA_ID"] == "EZR012345:6"
        assert heat_controls[7]["_HEATAREA_ID"] == "EZR012345:7"
        assert heat_controls[8]["_HEATAREA_ID"] == "EZR012345:8"
        assert heat_controls[9]["_HEATAREA_ID"] is None

        io_devices = {io["NR"]: io for io in base.io_devices}
        assert io_devices[1]["_HEATAREA_ID"] == "EZR012345:7"
        assert io_devices[2]["_HEATAREA_ID"] == "EZR012345:5"
        assert io_devices[3]["_HEATAREA_ID"] == "EZR012345:6"
        assert io_devices[4]["_HEATAREA_ID"] == "EZR012345:8"
        assert io_devices[5]["_HEATAREA_ID"] == "EZR012345:1"
        assert io_devices[6]["_HEATAREA_ID"] == "EZR012345:4"


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_ensure_static_data() -> None:
    """Test _ensure_static_data"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    with pytest.raises(RuntimeError):
        print(base.name)


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_get_heat_areas() -> None:
    """Test getting heat areas"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()
    heat_areas = list(base.heat_areas)
    assert len(heat_areas) > 0
    for heat_area in heat_areas:
        assert heat_area["NR"]
        assert heat_area["ID"].endswith(f":{heat_area['NR']}")


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_update_heat_areas() -> None:
    """Test updating heat areas"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    t_target = round(heat_area["T_TARGET"] + 0.2, 1)
    await base.update_heat_area(heat_area["ID"], {"T_TARGET": t_target})
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    assert heat_area["T_TARGET"] == t_target

    t_target = round(heat_area["T_TARGET"] - 0.2, 1)
    await base.update_heat_area(int(heat_area["ID"].split(":")[-1]), {"T_TARGET": t_target})
    await base.update_data()
    heat_area = list(base.heat_areas)[0]
    assert heat_area["T_TARGET"] == t_target


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_get_set_cooling() -> None:
    """Test getting and setting cooling mode"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()
    await base.set_cooling(True)
    assert base.cooling is True

    await base.update_data()
    assert base.cooling is True

    await base.set_cooling(False)
    assert base.cooling is False

    await base.update_data()
    assert base.cooling is False


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_set_cooling_timeout() -> None:
    """Test getting and setting cooling mode"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS, command_timeout=0.1, command_poll_interval=0.1)
    await base.update_data()
    with pytest.raises(TimeoutError):
        await base.set_cooling(True)
        await base.set_cooling(False)


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_command() -> None:
    """Test getting and setting cooling mode"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()
    await base.send_command("<COOLING>1</COOLING>")
    await asyncio.sleep(3)
    await base.send_command("<COOLING>0</COOLING>")


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_update_lock() -> None:
    """Test update lock"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()
    coros = [base.set_cooling(True), base.update_data(), base.set_cooling(False), base.set_cooling(True), base.update_data()]
    await asyncio.gather(*coros)


@pytest.mark.asyncio
@pytest.mark.skipif(not ALPHA2_BASE_ADDRESS, reason="ALPHA2_BASE_ADDRESS not set in environment")
async def test_set_datetime() -> None:
    """Test set datetime"""
    assert ALPHA2_BASE_ADDRESS
    base = Alpha2Base(ALPHA2_BASE_ADDRESS)
    await base.update_data()

    value = datetime(2010, 1, 1, 0, 0, 0)
    await base.set_datetime(value)
    await asyncio.sleep(5)
    await base.update_data()
    assert base.static_data
    base_dt = datetime.strptime(base.static_data["Devices"]["Device"]["DATETIME"], "%Y-%m-%dT%H:%M:%S")
    assert abs((base_dt - value).total_seconds()) < 10

    await base.set_datetime()
    await asyncio.sleep(5)
    await base.update_data()
    assert base.static_data
    base_dt = datetime.strptime(base.static_data["Devices"]["Device"]["DATETIME"], "%Y-%m-%dT%H:%M:%S")
    assert abs((base_dt - datetime.now()).total_seconds()) < 10
