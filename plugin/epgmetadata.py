from __future__ import absolute_import

import re


_SEASON_EPISODE_PATTERNS = (
	re.compile(r"\bS(?:eason|taffel)?\s*0*(\d+)\s*[-._ ]*E(?:pisode)?\s*0*(\d+)(?:\s*/\s*(\d+))?\b", re.IGNORECASE),
	re.compile(r"\b(?:Staffel|Season)\s*0*(\d+)\s*[,;:/-]?\s*(?:Folge|Episode)\s*0*(\d+)(?:\s*/\s*(\d+))?\b", re.IGNORECASE),
)
_COMPACT_SEASON_EPISODE_PATTERN = re.compile(r"\b0*(\d+)\s*[xX]\s*0*(\d+)(?:\s*/\s*(\d+))?\b")
_EPISODE_PATTERN = re.compile(r"\b(?:Folge|Episode|Ep\.)\s*0*(\d+)(?:\s*/\s*(\d+))?\b", re.IGNORECASE)


def episode_numbers(*texts):
	"""Return an onscreen and XMLTV episode number found in EPG text."""
	for text in texts:
		if not text:
			continue
		for pattern in _SEASON_EPISODE_PATTERNS:
			match = pattern.search(text)
			if match:
				season = int(match.group(1))
				episode = int(match.group(2))
				total = int(match.group(3)) if match.group(3) else None
				if season < 1 or episode < 1 or (total is not None and episode > total):
					continue
				onscreen = "S%02dE%02d" % (season, episode)
				episode_part = "%d/%d" % (episode - 1, total) if total else str(episode - 1)
				return onscreen, "%d.%s." % (season - 1, episode_part)

	# Compact notation is ambiguous with quantities such as "2x 120" and is
	# therefore accepted only in the programme title or short description.
	for text in texts[:2]:
		if not text:
			continue
		match = _COMPACT_SEASON_EPISODE_PATTERN.search(text)
		if match:
			season = int(match.group(1))
			episode = int(match.group(2))
			total = int(match.group(3)) if match.group(3) else None
			if season < 1 or episode < 1 or (total is not None and episode > total):
				continue
			onscreen = "S%02dE%02d" % (season, episode)
			episode_part = "%d/%d" % (episode - 1, total) if total else str(episode - 1)
			return onscreen, "%d.%s." % (season - 1, episode_part)

	for text in texts:
		if not text:
			continue
		match = _EPISODE_PATTERN.search(text)
		if match:
			episode = int(match.group(1))
			total = int(match.group(2)) if match.group(2) else None
			if episode < 1 or (total is not None and episode > total):
				continue
			onscreen = "E%02d" % episode
			episode_part = "%d/%d" % (episode - 1, total) if total else str(episode - 1)
			return onscreen, ".%s." % episode_part

	return None, None


def _items(value):
	if value is None:
		return []
	if isinstance(value, (list, tuple)):
		if isinstance(value, tuple) and len(value) == 2 and not isinstance(value[0], (list, tuple)):
			return [value]
		return value
	return [value]


def genres(genre_data):
	"""Convert Enigma2 DVB content descriptors to displayable categories."""
	try:
		from Components.Converter.genre import getGenreStringSub
	except ImportError:
		return []

	output = []
	for item in _items(genre_data):
		try:
			if hasattr(item, "getLevel1"):
				level1 = int(item.getLevel1())
				level2 = int(item.getLevel2())
			else:
				level1 = int(item[0])
				level2 = int(item[1])
		except (AttributeError, IndexError, TypeError, ValueError):
			continue
		if level1 < 1 or level1 > 15:
			continue
		try:
			name = getGenreStringSub(level1, level2)
		except Exception:
			continue
		if name and name not in output:
			output.append(name)
	return output


def ratings(parental_data):
	"""Convert DVB parental descriptors to (country, minimum age) pairs."""
	output = []
	for item in _items(parental_data):
		try:
			if hasattr(item, "getCountryCode"):
				country = item.getCountryCode()
				raw_rating = int(item.getRating())
			else:
				country = item[0]
				raw_rating = int(item[1])
		except (AttributeError, IndexError, TypeError, ValueError):
			continue
		if not country or raw_rating < 1 or raw_rating > 15:
			continue
		rating = (str(country).upper(), raw_rating + 3)
		if rating not in output:
			output.append(rating)
	return output
