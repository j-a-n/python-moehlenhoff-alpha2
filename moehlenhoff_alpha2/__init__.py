# -*- coding: utf-8 -*-
"""
(C) 2020 by Jan Schneider (oss@janschneider.net)
Released under the GNU General Public License v3.0
"""

import asyncio
import collections
import aiohttp
import xmltodict
import logging

logger = logging.getLogger(__name__)

__version__ = "1.0.2"

class Alpha2Base:
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
                    if _types[k] is bool and type(data[k]) is not bool:
                        data[k] = "1" if data[k] else "0"
                        continue
                    elif _types[k] is float and type(data[k]) is not float:
                        data[k] = "{data[k]:0.1f}"
                        continue
                data[k] = str(data[k])
        return data

    async def _fetch_static_data(self):
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(f"{self.base_url}/data/static.xml") as response:
                data = await response.text()
                self.static_data = xmltodict.parse(data)
                if not "HEATAREA" in self.static_data["Devices"]["Device"]:
                    self.static_data["Devices"]["Device"]["HEATAREA"] = []
                if not isinstance(self.static_data["Devices"]["Device"]["HEATAREA"], list):
                    self.static_data["Devices"]["Device"]["HEATAREA"] = [
                        self.static_data["Devices"]["Device"]["HEATAREA"]
                    ]
                logger.debug(
                    "Static data fetched from '%s', device name is '%s', %d heatareas found",
                    self.base_url,
                    self.static_data["Devices"]["Device"]["NAME"],
                    len(self.static_data["Devices"]["Device"]["HEATAREA"])
                )

    def _ensure_static_data(self):
        if self.static_data:
            return
        future = asyncio.run_coroutine_threadsafe(self.update_data(), asyncio.get_event_loop())
        future.result(timeout=self._timeout.total)

    async def _send_command(self, device_id, command):
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
        await self._fetch_static_data()

    @property
    def name(self):
        self._ensure_static_data()
        return self.static_data["Devices"]["Device"]["NAME"]

    @property
    def heatareas(self):
        self._ensure_static_data()
        device = self.static_data["Devices"]["Device"]
        for ha in device["HEATAREA"]:
            ha = dict(ha)
            self._types_from_xml("HEATAREA", ha)
            ha["NR"] = int(ha["@nr"])
            del ha["@nr"]
            ha["ID"] = f"{device['ID']}:{ha['NR']}"
            yield ha

    async def update_heatarea(self, heatarea_id, settings):
        device_id, nr = heatarea_id.split(":")
        command = f'<HEATAREA nr="{nr}">'
        self._types_for_xml("HEATAREA", settings)
        for k, v in settings.items():
            command += f"<{k}>{v}</{k}>"
        command += "</HEATAREA>"
        await self._send_command(device_id, command)
