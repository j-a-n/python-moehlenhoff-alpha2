# -*- coding: utf-8 -*-
"""
(C) 2020 by Jan Schneider (oss@janschneider.net)
Released under the GNU General Public License v3.0
"""

import logging
import asyncio
import aiohttp
import xmltodict


logger = logging.getLogger(__name__)

__version__ = "1.1.0"


class Alpha2Base:
    """Class representing one alpha2 base"""
    _TYPES = {
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
        }
    }

    def __init__(self, host):
        self.base_url = f"http://{host}"
        self.static_data = None
        self._timeout = aiohttp.ClientTimeout(total=10)

    def _types_from_xml(self, entity_type, data):
        _types = self._TYPES.get(entity_type)
        if _types:
            for k in data:
                if k in _types:
                    if _types[k] is bool:
                        data[k] = data[k] == "1"
                    else:
                        data[k] = _types[k](data[k])
        return data

    def _types_for_xml(self, entity_type, data):
        _types = self._TYPES.get(entity_type)
        if _types:
            for k in data:
                if k in _types:
                    if _types[k] is bool and not isinstance(data[k], bool):
                        data[k] = "1" if data[k] else "0"
                        continue
                    if _types[k] is float and not isinstance(data[k], float):
                        data[k] = "{data[k]:0.1f}"
                        continue
                data[k] = str(data[k])
        return data

    async def _fetch_static_data(self):
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(f"{self.base_url}/data/static.xml") as response:
                data = await response.text()
                self.static_data = xmltodict.parse(data)
                for _type in ("HEATAREA", "HEATCTRL"):
                    if _type not in self.static_data["Devices"]["Device"]:
                        self.static_data["Devices"]["Device"][_type] = []
                    if not isinstance(self.static_data["Devices"]["Device"][_type], list):
                        self.static_data["Devices"]["Device"][_type] = [
                            self.static_data["Devices"]["Device"][_type]
                        ]
                logger.debug(
                    "Static data fetched from '%s', device name is '%s', %d heat_areas found",
                    self.base_url,
                    self.static_data["Devices"]["Device"]["NAME"],
                    len(self.static_data["Devices"]["Device"]["HEATAREA"])
                )

    def _ensure_static_data(self):
        """Ensure that static data is available"""
        if self.static_data:
            return
        future = asyncio.run_coroutine_threadsafe(self.update_data(), asyncio.get_event_loop())
        future.result(timeout=self._timeout.total)

    async def _send_command(self, device_id, command):
        """Send a command to the base"""
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            "<Devices><Device>"
            f"<ID>{device_id}</ID>{command}"
            "</Device></Devices>"
        )
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.post(
                f"{self.base_url}/data/changes.xml", data=xml.encode("utf-8")
            ) as response:
                return await response.text()

    async def update_data(self):
        """Update local data"""
        await self._fetch_static_data()

    @property
    def name(self):
        """Return the name of the base"""
        self._ensure_static_data()
        return self.static_data["Devices"]["Device"]["NAME"]

    @property
    def id(self):  # pylint: disable=invalid-name
        """Return the id of the base"""
        self._ensure_static_data()
        return self.static_data["Devices"]["Device"]["ID"]

    @property
    def heat_areas(self):
        """Return all heat areas"""
        self._ensure_static_data()
        device = self.static_data["Devices"]["Device"]
        for heat_area in device["HEATAREA"]:
            heat_area = dict(heat_area)
            self._types_from_xml("HEATAREA", heat_area)
            heat_area["NR"] = int(heat_area["@nr"])
            del heat_area["@nr"]
            heat_area["ID"] = f"{device['ID']}:{heat_area['NR']}"
            heat_area["_HEATCTRL_STATE"] = 0
            for heatctrl in device["HEATCTRL"]:
                if heatctrl["INUSE"] and int(heatctrl["HEATAREA_NR"]) == heat_area["NR"]:
                    heat_area["_HEATCTRL_STATE"] = int(heatctrl["HEATCTRL_STATE"])
                    if heat_area["_HEATCTRL_STATE"]:
                        break
            yield heat_area

    @property
    def cooling(self):
        """Return if cooling mode is active"""
        self._ensure_static_data()
        return int(self.static_data["Devices"]["Device"]["COOLING"]) == 1

    async def set_cooling(self, value: bool):
        """Set cooling mode"""
        # Needs <RELAIS><FUNCTION>1</FUNCTION></RELAIS>
        value = 1 if value else 0
        command = f'<COOLING>{value}</COOLING>'
        await self._send_command(self.id, command)
        self.static_data["Devices"]["Device"]["COOLING"] = value

    async def update_heat_area(self, heat_area_id, settings):
        """Update heat area settings on base"""
        device_id = None
        ha_nr = None
        if ":" in heat_area_id:
            device_id, ha_nr = heat_area_id.split(":")
        else:
            device_id = self.id
            ha_nr = heat_area_id
        command = f'<HEATAREA nr="{ha_nr}">'
        self._types_for_xml("HEATAREA", settings)
        for sttr, val in settings.items():
            command += f"<{sttr}>{val}</{sttr}>"
        command += "</HEATAREA>"
        await self._send_command(device_id, command)
