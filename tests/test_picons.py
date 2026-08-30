from __future__ import absolute_import

import sys
import tempfile
import unittest
from os import path


sys.path.insert(0, path.join(path.dirname(path.dirname(path.abspath(__file__))), "plugin"))
import picons


class PiconTest(unittest.TestCase):
	def setUp(self):
		self.original_resolver = picons._get_picon_name
		picons._picon_cache.clear()

	def tearDown(self):
		picons._get_picon_name = self.original_resolver
		picons._picon_cache.clear()

	def test_existing_enigma_picon_is_exposed_by_channel_url(self):
		with tempfile.NamedTemporaryFile(suffix=".png") as picon_file:
			picons._get_picon_name = lambda service_ref: picon_file.name
			service_ref = "1:0:19:283D:3FB:1:C00000:0:0:0:"
			self.assertEqual(picon_file.name, picons.find_picon(service_ref))
			self.assertEqual("http://receiver.local:6083/picon/1.png", picons.picon_url("receiver.local", "6083", "1", service_ref))

	def test_missing_and_iptv_picons_are_omitted(self):
		picons._get_picon_name = lambda service_ref: ""
		self.assertEqual("", picons.find_picon("1:0:19:FFFF:"))
		self.assertEqual("", picons.find_picon("http://example.test/stream"))


if __name__ == "__main__":
	unittest.main()
