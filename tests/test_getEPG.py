from __future__ import absolute_import

import importlib.util
import sys
import types
import unittest
from os import path
from xml.etree import ElementTree


ROOT = path.dirname(path.dirname(path.abspath(__file__)))
PLUGIN = path.join(ROOT, "plugin")
PACKAGE_NAME = "hrtunerproxy_test"


def _load_module(name, filename):
	spec = importlib.util.spec_from_file_location(name, filename)
	module = importlib.util.module_from_spec(spec)
	sys.modules[name] = module
	spec.loader.exec_module(module)
	return module


package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [PLUGIN]
package.tunerports = {"DVB-S": "6083"}
package.getHost = lambda: "receiver.local"
sys.modules[PACKAGE_NAME] = package

six_module = types.ModuleType("six")
six_module.text_type = str
six_module.binary_type = bytes
sys.modules["six"] = six_module

enigma = types.ModuleType("enigma")
enigma.eEPGCache = type("eEPGCache", (), {"getInstance": staticmethod(lambda: None)})
sys.modules["enigma"] = enigma

components = types.ModuleType("Components")
components.__path__ = []
config_module = types.ModuleType("Components.config")
config_module.config = types.SimpleNamespace(hrtunerproxy=types.SimpleNamespace(
	debug=types.SimpleNamespace(value=False),
	provide_picons=types.SimpleNamespace(value=False),
))
converter = types.ModuleType("Components.Converter")
converter.__path__ = []
genre_module = types.ModuleType("Components.Converter.genre")
genre_module.getGenreStringSub = lambda level1, level2: "Drama" if (level1, level2) == (1, 4) else "Other"
sys.modules["Components"] = components
sys.modules["Components.config"] = config_module
sys.modules["Components.Converter"] = converter
sys.modules["Components.Converter.genre"] = genre_module

lineup_module = types.ModuleType(PACKAGE_NAME + ".getLineup")
lineup_module.getLineup = lambda bouquet=None: None
sys.modules[PACKAGE_NAME + ".getLineup"] = lineup_module

_load_module(PACKAGE_NAME + ".epgmetadata", path.join(PLUGIN, "epgmetadata.py"))
get_epg_module = _load_module(PACKAGE_NAME + ".getEPG", path.join(PLUGIN, "getEPG.py"))


class FakeEPGCache(object):
	def lookupEvent(self, query):
		return [(42, 1700000000, 3600, "Example Show", "Staffel 2, Folge 3", "Zukunftspläne im Gepäck".encode("utf-8"), [(1, 4)], [("DEU", 9)])]


class StarTrekEPGCache(object):
	def lookupEvent(self, query):
		return [(43, 1700003600, 1500, "Star Trek: Lower Decks", "Star Trek: Lower Decks", "Staffel-Premiere. Ungefähr drei Monate nach den Ereignissen von Staffel Eins wird die USS Cerritos auf eine Mission entsandt.\r", [(3, 3)], None)]


class GetEPGTest(unittest.TestCase):
	def test_xmltv_contains_series_metadata(self):
		sys.modules["Components.Converter.genre"].getGenreStringSub = lambda level1, level2: "Drama"
		epg = get_epg_module.getEPG.__new__(get_epg_module.getEPG)
		epg.dvbtype = "DVB-S"
		epg.bouquet_name = "test"
		epg.channels = [("1", "Example Channel", "1:0:1:TEST:", "DVB-S")]
		epg.epgcache = FakeEPGCache()

		root = ElementTree.fromstring(epg.xmltv())
		programme = root.find("programme")
		self.assertEqual("Example Show", programme.findtext("title"))
		self.assertEqual("Zukunftspläne im Gepäck", programme.findtext("desc"))
		self.assertEqual(["Drama", "Series"], [item.text for item in programme.findall("category")])
		self.assertEqual("S02E03", programme.find("episode-num[@system='onscreen']").text)
		self.assertEqual("1.2.", programme.find("episode-num[@system='xmltv_ns']").text)
		self.assertEqual("12+", programme.find("rating/value").text)

	def test_utf8_bytes_are_decoded_before_xml_output(self):
		self.assertEqual("Zukunftspläne im Gepäck", get_epg_module._xml("Zukunftspläne im Gepäck".encode("utf-8")))
		self.assertEqual("first\nsecond", get_epg_module._text("first\rsecond"))
		self.assertEqual("validtext", get_epg_module._text("valid\x00text"))
		self.assertEqual("Ära in Österreich: verrät Zukunftspläne und genießt", get_epg_module._text("Ã\x84ra in Ã\x96sterreich: verr¤t ZukunftsplÃ¤ne und genieÃ\x9ft"))
		self.assertEqual("„quoted“ …", get_epg_module._text("â\x80\x9equotedâ\x80\x9c â\x80¦"))
		self.assertEqual("culture – \"quoted\"", get_epg_module._text("culture â± \"quoted\""))
		self.assertEqual("8.99 €", get_epg_module._text("8.99 ¤"))

	def test_description_tag_is_well_formed_and_duplicate_subtitle_is_omitted(self):
		epg = get_epg_module.getEPG.__new__(get_epg_module.getEPG)
		epg.dvbtype = "DVB-S"
		epg.bouquet_name = "test"
		epg.channels = [("32", "Comedy Central", "1:0:1:TEST:", "DVB-S")]
		epg.epgcache = StarTrekEPGCache()

		xml = epg.xmltv()
		programme = ElementTree.fromstring(xml).find("programme")
		self.assertIsNone(programme.find("sub-title"))
		self.assertTrue(programme.findtext("desc").startswith("Staffel-Premiere."))
		self.assertNotIn("</desc>sc>", xml)

	def test_existing_channel_picon_is_added_to_xmltv(self):
		epg = get_epg_module.getEPG.__new__(get_epg_module.getEPG)
		epg.dvbtype = "DVB-S"
		epg.bouquet_name = "test"
		epg.channels = [("1", "Example Channel", "1:0:1:TEST:", "DVB-S")]
		epg.epgcache = FakeEPGCache()
		original_picon_url = get_epg_module.picon_url
		get_epg_module.picon_url = lambda host, port, number, service_ref: "http://receiver.local:6083/picon/1.png"
		config_module.config.hrtunerproxy.provide_picons.value = True
		try:
			root = ElementTree.fromstring(epg.xmltv())
		finally:
			config_module.config.hrtunerproxy.provide_picons.value = False
			get_epg_module.picon_url = original_picon_url
		self.assertEqual("http://receiver.local:6083/picon/1.png", root.find("channel/icon").get("src"))

	def test_channel_picons_are_disabled_by_default(self):
		epg = get_epg_module.getEPG.__new__(get_epg_module.getEPG)
		epg.dvbtype = "DVB-S"
		epg.bouquet_name = "test"
		epg.channels = [("1", "Example Channel", "1:0:1:TEST:", "DVB-S")]
		epg.epgcache = FakeEPGCache()
		original_picon_url = get_epg_module.picon_url
		get_epg_module.picon_url = lambda host, port, number, service_ref: "http://receiver.local:6083/picon/1.png"
		try:
			root = ElementTree.fromstring(epg.xmltv())
		finally:
			get_epg_module.picon_url = original_picon_url
		self.assertIsNone(root.find("channel/icon"))


if __name__ == "__main__":
	unittest.main()
