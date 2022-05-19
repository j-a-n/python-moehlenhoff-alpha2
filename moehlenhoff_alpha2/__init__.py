# -*- coding: utf-8 -*-
"""
(C) 2022 by Jan Schneider (oss@janschneider.net)
Released under the GNU General Public License v3.0
"""

import time
from typing import Union, Generator, Dict
import logging
import asyncio
import aiohttp
import xmltodict


logger = logging.getLogger(__name__)

__version__ = "1.1.2"


class Alpha2Base:
    """Class representing one alpha2 base"""

    _TYPES = {
        "IODEVICE": {
            "IODEVICE_TYPE": int,
            "IODEVICE_ID": int,
            "IODEVICE_VERS_HW": str,
            "IODEVICE_VERS_SW": str,
            "HEATAREA_NR": int,
            "SIGNALSTRENGTH": int,
            "BATTERY": int,  # 0=empty, 1=weak, 2=good
            "IODEVICE_STATE": int,
            "IODEVICE_COMERROR": int,
            "ISON": bool,
        },
        "HEATCTRL": {
            "INUSE": bool,
            "HEATAREA_NR": int,
            "ACTOR": int,
            "ACTOR_PERCENT": int,
            "HEATCTRL_STATE": int,
        },
        "HEATAREA": {
            "BLOCK_HC": bool,
            "HEATAREA_NAME": str,
            "HEATAREA_MODE": int,
            "HEATAREA_STATE": int,
            "HEATINGSYSTEM": int,  # 0 FBH Standard - 1 FBH Niedrigenergie - 2 Radiator - 3 Konvektor passiv - 4 Konvektor aktiv
            "ISLOCKED": bool,
            "LIGHT": int,
            "LOCK_AVAILABLE": bool,
            "LOCK_CODE": str,
            "OFFSET": float,
            "PARTY": bool,
            "PARTY_REMAININGTIME": int,
            "PRESENCE": bool,
            "PROGRAM_SOURCE": int,
            "PROGRAM_WEEK": int,
            "PROGRAM_WEEKEND": int,
            "RPM_MOTOR": int,
            "SENSOR_EXT": int,  # 0 kein zusätzlicher Sensor - 1 Taupunktsensor - 2 Bodensensor - 3 Raumsensor
            "T_ACTUAL": float,
            "T_ACTUAL_EXT": float,
            "T_COOL_DAY": float,
            "T_COOL_NIGHT": float,
            "T_FLOOR_DAY": float,
            "T_HEAT_DAY": float,
            "T_HEAT_NIGHT": float,
            "T_TARGET": float,
            "T_TARGET_ADJUSTABLE": bool,
            "T_TARGET_BASE": float,
            "T_TARGET_MIN": float,
            "T_TARGET_MAX": float,
        },
    }
    _command_poll_interval = 2.0
    _command_timeout = 10.0
    _client_timeout = aiohttp.ClientTimeout(total=10)

    def __init__(self, host: str) -> None:
        self.base_url = f"http://{host}"
        self.static_data = None
        self._update_lock = asyncio.Lock()

    @classmethod
    def convert_types_from_xml(cls, entity_type: str, data: dict) -> dict:
        """Convert types in data structure from xlm"""
        _types = cls._TYPES.get(entity_type)
        if not _types:
            raise ValueError(f"Invalid entity type '{entity_type}'")
        data = data.copy()
        for attribute in data:
            if attribute in _types:
                if _types[attribute] is bool:
                    data[attribute] = bool(int(data[attribute]))
                else:
                    data[attribute] = _types[attribute](data[attribute])
        return data

    @classmethod
    def convert_types_for_xml(cls, entity_type: str, data: dict) -> dict:
        """Convert types in data structure for xlm"""
        _types = cls._TYPES.get(entity_type)
        if not _types:
            raise ValueError(f"Invalid entity type '{entity_type}'")
        data = data.copy()
        for attribute in data:
            if attribute in _types:
                if _types[attribute] is bool:
                    data[attribute] = (
                        "1" if data[attribute] and data[attribute] != "0" else "0"
                    )
                    continue
                if _types[attribute] is float:
                    data[attribute] = f"{float(data[attribute]):0.1f}"
                    continue
            data[attribute] = str(data[attribute])
        return data

    async def _send_command(self, device_id: str, command: str) -> str:
        """Send a command to the base with device_id"""
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Devices><Device>"
            f"<ID>{device_id}</ID>{command}"
            "</Device></Devices>"
        )
        async with aiohttp.ClientSession(timeout=self._client_timeout) as session:
            for trynum in (1, 2):
                try:
                    async with session.post(
                        f"{self.base_url}/data/changes.xml", data=xml.encode("utf-8")
                    ) as response:
                        response.raise_for_status()
                        return await response.text()
                except (UnicodeDecodeError, aiohttp.ClientError):
                    if trynum == 2:
                        raise

    async def send_command(self, command: str) -> str:
        """Send a command to the base"""
        async with self._update_lock:
            return await self._send_command(self.id, command)

    def _ensure_static_data(self) -> None:
        """Ensure that static data is available"""
        if not self.static_data:
            raise RuntimeError("Static data not available")

    async def _fetch_static_data(self) -> str:
        async with aiohttp.ClientSession(timeout=self._client_timeout) as session:
            for trynum in (1, 2):
                try:
                    async with session.get(
                        f"{self.base_url}/data/static.xml"
                    ) as response:
                        response.raise_for_status()
                        return await response.text()
                except (UnicodeDecodeError, aiohttp.ClientError):
                    if trynum == 2:
                        raise

    async def _get_static_data(self) -> dict:
        """Get and process static data"""
        data = await self._fetch_static_data()
        data = xmltodict.parse(data)
        for _type in ("HEATAREA", "HEATCTRL", "IODEVICE"):
            if not isinstance(data["Devices"]["Device"][_type], list):
                data["Devices"]["Device"][_type] = [data["Devices"]["Device"][_type]]
        return data

    async def update_data(self) -> None:
        """Update local data"""
        async with self._update_lock:
            self.static_data = await self._get_static_data()
            logger.debug(
                "Static data updated from '%s', device name is '%s', %d heat areas, %d heat controls and %d io devices found",
                self.base_url,
                self.name,
                len(self.static_data["Devices"]["Device"]["HEATAREA"]),
                len(self.static_data["Devices"]["Device"]["HEATCTRL"]),
                len(self.static_data["Devices"]["Device"]["IODEVICE"]),
            )

    @property
    def name(self) -> str:
        """Return the name of the base"""
        self._ensure_static_data()
        return self.static_data["Devices"]["Device"]["NAME"]

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        """Return the id of the base"""
        self._ensure_static_data()
        return self.static_data["Devices"]["Device"]["ID"]

    @property
    def io_devices(self) -> Generator[Dict, None, None]:
        """Return all io devices"""
        self._ensure_static_data()
        device = self.static_data["Devices"]["Device"]
        for io_device in device["IODEVICE"]:
            io_device = self.convert_types_from_xml("IODEVICE", io_device)
            io_device["NR"] = int(io_device["@nr"])
            del io_device["@nr"]
            io_device["ID"] = f"{device['ID']}:{io_device['NR']}"
            io_device["_HEATAREA_ID"] = f"{device['ID']}:{io_device['HEATAREA_NR']}" if io_device['HEATAREA_NR'] else None
            yield io_device

    @property
    def heat_controls(self) -> Generator[Dict, None, None]:
        """Return all heat controls"""
        self._ensure_static_data()
        device = self.static_data["Devices"]["Device"]
        for heat_control in device["HEATCTRL"]:
            heat_control = self.convert_types_from_xml("HEATCTRL", heat_control)
            heat_control["NR"] = int(heat_control["@nr"])
            del heat_control["@nr"]
            heat_control["ID"] = f"{device['ID']}:{heat_control['NR']}"
            heat_control["_HEATAREA_ID"] = f"{device['ID']}:{heat_control['HEATAREA_NR']}" if heat_control['HEATAREA_NR'] else None
            yield heat_control

    @property
    def heat_areas(self) -> Generator[Dict, None, None]:
        """Return all heat areas"""
        self._ensure_static_data()
        device = self.static_data["Devices"]["Device"]
        for heat_area in device["HEATAREA"]:
            heat_area = self.convert_types_from_xml("HEATAREA", heat_area)
            heat_area["NR"] = int(heat_area["@nr"])
            del heat_area["@nr"]
            heat_area["ID"] = f"{device['ID']}:{heat_area['NR']}"
            heat_area["_HEATCTRL_STATE"] = 0
            for heatctrl in device["HEATCTRL"]:
                if (
                    heatctrl["INUSE"]
                    and int(heatctrl["HEATAREA_NR"]) == heat_area["NR"]
                ):
                    heat_area["_HEATCTRL_STATE"] = int(heatctrl["HEATCTRL_STATE"])
                    if heat_area["_HEATCTRL_STATE"]:
                        break
            yield heat_area

    @property
    def cooling(self) -> bool:
        """Return if cooling mode is active"""
        self._ensure_static_data()
        return int(self.static_data["Devices"]["Device"]["COOLING"]) == 1

    async def set_cooling(self, value: bool) -> None:
        """Set cooling mode"""
        # Needs <RELAIS><FUNCTION>1</FUNCTION></RELAIS>
        value = 1 if value else 0
        self.static_data["Devices"]["Device"]["COOLING"] = value
        command = f"<COOLING>{value}</COOLING>"
        async with self._update_lock:
            await self._send_command(self.id, command)
            start = time.time()
            while True:
                await asyncio.sleep(self._command_poll_interval)
                data = await self._get_static_data()
                if int(data["Devices"]["Device"]["COOLING"]) == value:
                    self.static_data = data
                    break
                elapsed = time.time() - start
                if elapsed > self._command_timeout:
                    raise TimeoutError(
                        f"Timed out after {elapsed:0.0f} seconds while waiting for command to take effect"
                    )

    async def update_heat_area(self, heat_area_id: Union[str, int], attributes: dict):
        """Update heat area attributes on base"""
        heat_area_id = str(heat_area_id)
        device_id = None
        ha_nr = None
        if ":" in heat_area_id:
            device_id, ha_nr = heat_area_id.split(":")
        else:
            device_id = self.id
            ha_nr = heat_area_id
        command = f'<HEATAREA nr="{ha_nr}">'
        attributes = self.convert_types_for_xml("HEATAREA", attributes)
        for attr, val in attributes.items():
            command += f"<{attr}>{val}</{attr}>"
        command += "</HEATAREA>"
        async with self._update_lock:
            await self._send_command(device_id, command)
