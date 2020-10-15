# -*- coding: utf-8 -*-
#
# Copyright 2018-2020 Univention GmbH
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

Base class for all ASM models.
"""

from __future__ import absolute_import, unicode_literals
import inspect
from ..utils import get_ucr

try:
	from typing import Any, AnyStr, Dict, Iterable, Union
except ImportError:
	pass


class AsmModel(object):
	"""Base class for all ASM models."""

	header = ()  # type: Iterable[AnyStr]

	def __init__(self, *args, **kwargs):  # type: (*Any, **Any) -> None
		pass

	def __repr__(self):  # type: () -> AnyStr
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
	def from_dn(cls, dn, *args, **kwargs):  # type: (AnyStr, *Any, **Any) -> AsmModel
		"""
		Get AsmModel object created from data in LDAP object.

		:param str dn: DN to object to represent
		:return: AsmModel instance
		:rtype: AsmModel
		"""
		raise NotImplementedError()

	def as_csv_line(self):  # type: () -> Iterable[AnyStr]
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

	def as_dict(self):  # type: () -> Dict[AnyStr, AnyStr]
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


class AnonymizeMixIn(object):
	ucr_anonymize_key_base = ''

	@classmethod
	def anonymize(cls, user, ldap_attrs, **kwargs):
		# type: (ucsschool.lib.models.user.User, Dict[AnyStr, Any], **Any) -> Dict[AnyStr, AnyStr]
		"""
		Change values of function arguments to anonymize/pseudonymize user if
		UCRV asm/attributes/<staff/student>/anonymize is true. Will return
		unchanged function arguments otherwise.

		:param ucsschool.lib.models.user.User user: user object
		:param dict ldap_attrs: dictionary with the users LDAP attributes
		:return: dictionary with [modified] function arguments
		:rtype: dict
		:raises NotImplementedError: if cls.ucr_anonymize_key_base is unset
		"""
		ucr = get_ucr()
		if ucr.is_true(cls.ucr_anonymize_key_base):
			for k, v in cls.anonymize_mapping().items():
				if v and v.startswith('%'):
					attr = v[1:].strip()
					try:
						v = ldap_attrs[attr][0]
					except KeyError:
						raise ValueError('Attribute {!r} not found in LDAP object of {}.'.format(attr, user))
					except IndexError:
						raise ValueError('Attribute {!r} empty in LDAP object of {}.'.format(attr, user))
				kwargs[k] = v
		return kwargs

	@classmethod
	def anonymize_mapping(cls):  # type: () -> Dict[AnyStr, Union[AnyStr, None]]
		if not cls.ucr_anonymize_key_base:
			raise NotImplementedError('Class attribute "ucr_anonymize_key_base" must be set.')
		cls.ucr_anonymize_key_base = cls.ucr_anonymize_key_base.rstrip('/')
		ucr = get_ucr()
		res = {
			'first_name': ucr.get('{}/first_name'.format(cls.ucr_anonymize_key_base), '%uid'),
			'middle_name': ucr.get('{}/middle_name'.format(cls.ucr_anonymize_key_base), None),
			'last_name': ucr.get('{}/last_name'.format(cls.ucr_anonymize_key_base), 'No Name'),
			'email_address': ucr.get('{}/email_address'.format(cls.ucr_anonymize_key_base), None),
			'sis_username': ucr.get('{}/sis_username'.format(cls.ucr_anonymize_key_base), '%uid'),
		}
		return res
