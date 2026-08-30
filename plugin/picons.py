from __future__ import absolute_import

from os.path import isfile, join


try:
	from Components.Renderer.Picon import getPiconName as _get_picon_name
except Exception:
	_get_picon_name = None


_PICON_DIRECTORIES = (
	"/usr/share/enigma2/picon",
	"/picon",
	"/data/picon",
	"/media/hdd/picon",
	"/media/usb/picon",
	"/media/sdcard/picon",
)
_picon_cache = {}


def _service_key(service_ref):
	fields = (service_ref or "").split(":", 10)[:10]
	if len(fields) < 10:
		return ""
	return "_".join(fields)


def find_picon(service_ref):
	"""Return the local PNG used by Enigma2 for a service reference."""
	if not service_ref or "http" in service_ref:
		return ""
	if service_ref in _picon_cache:
		return _picon_cache[service_ref]

	picon_path = ""
	if _get_picon_name is not None:
		try:
			candidate = _get_picon_name(service_ref)
			if candidate and candidate.lower().endswith(".png") and isfile(candidate):
				picon_path = candidate
		except Exception:
			pass

	if not picon_path:
		key = _service_key(service_ref)
		if key:
			for directory in _PICON_DIRECTORIES:
				candidate = join(directory, "%s.png" % key)
				if isfile(candidate):
					picon_path = candidate
					break

	if picon_path:
		_picon_cache[service_ref] = picon_path
	return picon_path


def picon_url(host, port, channel_number, service_ref):
	if not find_picon(service_ref):
		return ""
	return "http://%s:%s/picon/%s.png" % (host, port, channel_number)


def channel_picon(dvbtype, bouquet_name, channel_number):
	"""Resolve a channel-number URL to a local picon without exposing paths."""
	from .getLineup import getLineup

	for number, channel_name, service_ref, channel_type in getLineup(bouquet=bouquet_name).output():
		if str(number) != str(channel_number):
			continue
		if dvbtype == "iptv" and "http" not in service_ref:
			continue
		if dvbtype in ("multi", "iptv", channel_type):
			return find_picon(service_ref)
	return ""
