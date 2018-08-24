#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Copyright 2018 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

"""
Univention Apple School Manager Connector

Base class for all OneRoster models.
"""

from __future__ import absolute_import, unicode_literals
import inspect

try:
	from typing import AnyStr, Dict, Iterable
except ImportError:
	pass


class OneRosterModel(object):
	"""Base class for all OneRoster models."""

	header = ()

	def __init__(self, *args, **kwargs):  # type(*Any, **Any) -> None
		pass

	def __repr__(self):  # type () -> str
		if not self.header:
			members = [
				m for m in inspect.getmembers(self, predicate=lambda x: not inspect.ismethod(x))
				if not m[0].startswith('_') and m[0] != 'header'
			]
		else:
			members = zip(self.header, [getattr(self, m) for m in self.header])
		return '{}({})'.format(
			self.__class__.__name__,
			', '.join('{}={!r}'.format(k, v) for k, v in members)
		)

	def get_header(self):  # type: () -> Iterable[AnyStr]
		"""
		Get the header for a CSV representation of the object.

		:return: CSV header as list of strings
		:rtype: list(str)
		"""
		return self.header

	@classmethod
	def from_dn(cls, dn, *args, **kwargs):  # type (AnyStr) -> OneRosterModel
		"""
		Get OneRosterModel object created from data in LDAP object.

		:param str dn: DN to object to represent
		:return: OneRosterModel instance
		:rtype OneRosterModel
		"""
		raise NotImplementedError()

	def as_csv_line(self):  # type () -> Iterable[AnyStr]
		"""
		Get this object represented as a list of strings.

		This default implementation will work as long as names returned by
		:py:meth:`get_header()` match member names.

		:return: CSV line as list
		:rtype: list(str)
		"""
		try:
			return [getattr(self, member) or '' for member in self.get_header()]
		except AttributeError:
			raise NotImplementedError(
				'Default implementation of as_csv_line() cannot handle {} object.'.format(
					self.__class__.__name__)
			)

	def as_dict(self):  # type () -> Dict[AnyStr, AnyStr]
		"""
		Get this object represented as a dict of strings.

		This default implementation will work as long as names returned by
		:py:meth:`get_header()` match member names.

		:return: dictionary with header names as keys and object values
		:rtype: dict(str)
		"""
		try:
			return dict((member, getattr(self, member) or '') for member in self.get_header())
		except AttributeError:
			raise NotImplementedError(
				'Default implementation of as_csv_line() cannot handle {} object.'.format(
					self.__class__.__name__)
			)
