from __future__ import print_function
from __future__ import absolute_import

import time
import re
import six
try:
	from xml.sax.saxutils import escape
except:
	def escape(text):
		return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
from sys import modules

from enigma import eEPGCache
from Components.config import config

from . import tunerports, getHost
from .getLineup import getLineup
from .epgmetadata import episode_numbers, genres, ratings


_INVALID_XML_CHARS = re.compile(u"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_MOJIBAKE_REPLACEMENTS = (
	(u"Ã¤", u"ä"),
	(u"Ã¶", u"ö"),
	(u"Ã¼", u"ü"),
	(u"Ã\x84", u"Ä"),
	(u"Ã\x96", u"Ö"),
	(u"Ã\x9c", u"Ü"),
	(u"Ã\x9f", u"ß"),
	(u"Â\xa0", u"\xa0"),
	(u"â\x80\x9e", u"„"),
	(u"â\x80\x9c", u"“"),
	(u"â\x80\x9d", u"”"),
	(u"â\x80¦", u"…"),
	(u"â±", u"–"),
)


def _text(text):
	if text is None:
		return ""
	if isinstance(text, six.binary_type):
		text = text.decode("utf-8", "replace")
	else:
		text = six.text_type(text)
	# DVB text can contain bare carriage returns. Normalize them so a closing
	# XML tag cannot overwrite the start of its line in terminal-like clients.
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	# Some DVB providers expose already mis-decoded German UTF-8 text. Repair
	# only the observed unambiguous sequences. A bare currency sign is an
	# umlaut inside a word and a Euro sign elsewhere in these feeds.
	for mojibake, replacement in _MOJIBAKE_REPLACEMENTS:
		text = text.replace(mojibake, replacement)
	text = re.sub(u"(?<=\\w)¤(?=\\w)", u"ä", text, flags=re.UNICODE)
	text = text.replace(u"¤", u"€")
	return _INVALID_XML_CHARS.sub("", text)


def _xml(text):
	return escape(_text(text), {'"': "&quot;", "'": "&apos;"})


def _xmltv_time(timestamp):
	try:
		return time.strftime("%Y%m%d%H%M%S %z", time.localtime(int(timestamp)))
	except:
		return ""


class getEPG:
	def __init__(self, dvbtype, bouquet_name):
		self.dvbtype = dvbtype
		self.bouquet_name = bouquet_name
		self.channels = getLineup(bouquet=bouquet_name).output()
		self.epgcache = eEPGCache.getInstance()

	def _filtered_channels(self):
		output = []
		for channel in self.channels:
			if self.dvbtype == "iptv" and "http" not in channel[2]:
				continue
			if self.dvbtype in ("multi", "iptv", channel[3]):
				output.append(channel)
		return output

	def _events(self, service_ref):
		if not self.epgcache:
			return []
		try:
			# W and P expose DVB content and parental rating descriptors.
			return self.epgcache.lookupEvent(['IBDTSEWP', (service_ref, 0, -1, -1)]) or []
		except Exception as e:
			# Some older Enigma2 images do not support the additional fields.
			try:
				return self.epgcache.lookupEvent(['IBDTSE', (service_ref, 0, -1, -1)]) or []
			except Exception:
				pass
			if config.hrtunerproxy.debug.value:
				print("[HRTunerProxy] EPG lookup failed for %s: %s" % (service_ref, e))
			return []

	def xmltv(self):
		host = getHost()
		url = "http://%s:%s/epg.xml" % (host, tunerports[self.dvbtype])
		lines = [
			'<?xml version="1.0" encoding="UTF-8"?>',
			'<tv generator-info-name="HRTunerProxy" generator-info-url="%s">' % _xml(url)
		]

		channels = self._filtered_channels()
		for channel_number, channel_name, service_ref, channel_type in channels:
			lines.append('  <channel id="%s">' % _xml(channel_number))
			lines.append('    <display-name>%s</display-name>' % _xml(channel_name))
			lines.append('    <display-name>%s</display-name>' % _xml(channel_number))
			lines.append('  </channel>')

		for channel_number, channel_name, service_ref, channel_type in channels:
			if "http" in service_ref:
				continue
			for event in self._events(service_ref):
				if not event or len(event) < 5:
					continue
				begin = int(event[1])
				duration = int(event[2])
				stop = begin + duration
				title = _text(event[3])
				short_description = _text(event[4]) if len(event) > 4 else ""
				extended_description = _text(event[5]) if len(event) > 5 else ""
				genre_data = event[6] if len(event) > 6 else None
				parental_data = event[7] if len(event) > 7 else None

				if not title or duration <= 0:
					continue

				lines.append('  <programme start="%s" stop="%s" channel="%s">' % (_xmltv_time(begin), _xmltv_time(stop), _xml(channel_number)))
				lines.append('    <title>%s</title>' % _xml(title))
				if short_description and short_description != title:
					lines.append('    <sub-title>%s</sub-title>' % _xml(short_description))
				if extended_description:
					lines.append('    <desc>%s</desc>' % _xml(extended_description))
				elif short_description and short_description != title:
					lines.append('    <desc>%s</desc>' % _xml(short_description))
				onscreen, xmltv_ns = episode_numbers(title, short_description, extended_description)
				categories = genres(genre_data)
				if onscreen and "series" not in [category.lower() for category in categories]:
					categories.append("Series")
				for category in categories:
					lines.append('    <category>%s</category>' % _xml(category))
				if onscreen:
					lines.append('    <episode-num system="onscreen">%s</episode-num>' % _xml(onscreen))
					lines.append('    <episode-num system="xmltv_ns">%s</episode-num>' % _xml(xmltv_ns))
				for country, minimum_age in ratings(parental_data):
					lines.append('    <rating system="%s">' % _xml(country))
					lines.append('      <value>%d+</value>' % minimum_age)
					lines.append('    </rating>')
				lines.append('  </programme>')

		lines.append('</tv>')
		return "\n".join(lines)


def epgdata(dvbtype='', bouquet_name=''):
	epg = getEPG(dvbtype, bouquet_name)
	return epg.xmltv()


getepg = modules[__name__]
