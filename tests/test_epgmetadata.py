from __future__ import absolute_import

import sys
import types
import unittest
from os import path

sys.path.insert(0, path.join(path.dirname(path.dirname(path.abspath(__file__))), "plugin"))
from epgmetadata import episode_numbers, genres, ratings


class EPGMetadataTest(unittest.TestCase):
	def test_sxxexx_episode_number(self):
		self.assertEqual(("S02E03", "1.2."), episode_numbers("Example S02E03"))
		self.assertEqual(("S02E03", "1.2."), episode_numbers("Example", "2x03"))

	def test_german_episode_number_with_total(self):
		self.assertEqual(("S03E07", "2.6/12."), episode_numbers("Staffel 3, Folge 7/12"))

	def test_episode_without_season(self):
		self.assertEqual(("E04", ".3."), episode_numbers("Folge 4"))

	def test_invalid_episode_is_ignored(self):
		self.assertEqual((None, None), episode_numbers("Staffel 0, Folge 0"))
		self.assertEqual((None, None), episode_numbers("Shopping", "", "Product quantity 2x 120"))

	def test_genre_objects_are_converted(self):
		components = types.ModuleType("Components")
		converter = types.ModuleType("Components.Converter")
		genre_module = types.ModuleType("Components.Converter.genre")
		genre_module.getGenreStringSub = lambda level1, level2: "Genre %d.%d" % (level1, level2)
		sys.modules["Components"] = components
		sys.modules["Components.Converter"] = converter
		sys.modules["Components.Converter.genre"] = genre_module
		self.assertEqual(["Genre 1.4", "Genre 4.3"], genres([(1, 4), (4, 3)]))

	def test_dvb_parental_rating_adds_three_years(self):
		self.assertEqual([("DEU", 12)], ratings([("deu", 9)]))


if __name__ == "__main__":
	unittest.main()
