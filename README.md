# HRTunerProxy
Setup Enigma2 to act as HR Proxy Server.

## XMLTV guide

The guide is available as `/epg.xml` and `/xmltv.xml` on each configured tuner port. It exports programme descriptions, DVB categories, parental ratings, and common season/episode labels such as `S01E02`, `1x02`, and `Staffel 1, Folge 2`. Episode labels are emitted in both onscreen and `xmltv_ns` formats to improve DVR series matching.

Guide metadata is limited to information present in the receiver's EPG. If a broadcaster supplies no season or episode number, HRTunerProxy does not add one.

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=andyblac%40icloud%2ecom&lc=GB&currency_code=GBP&bn=PP%2dDonationsBF%3abtn_donateCC_LG%2egif%3aNonHosted)
