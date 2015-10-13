# -*- coding: utf-8 -*-
# Copyright (C) 2015 Yutaka Kamei
"""libldap.compat module

This module provides interfaces for python-ldap compatibility
"""

from .core import LDAP


def initialize(uri,
               trace_level=None,
               trace_file=None,
               trace_stack_limit=None):
    """
    :param uri:
        LDAP URI (e.g. `'ldap://localhost'`, `'ldaps://localhost'`, `'ldapi:///'`)
    :param trace_level:
        This parameter will be ignored
    :param trace_file:
        This parameter will be ignored
    :param trace_stack_limit:
        This parameter will be ignored
    """
    return LDAPObject(uri)


def open(host, port=389):
    initialize('ldap://%s:%d' % (host, port))


def get_option(option):
    ld = LDAP('ldap://localhost')
    return ld.get_option(option, is_global=True)


def set_option(option, invalue):
    ld = LDAP('ldap://localhost')
    return ld.set_option(option, invalue, is_global=True)


class LDAPObject(LDAP):
    pass
