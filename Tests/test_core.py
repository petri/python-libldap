# -*- coding: utf-8 -*-
# Copyright (C) 2015 Yutaka Kamei

import os
import time
import unittest
from datetime import datetime
from types import GeneratorType

from .environ import Environment, cacert_file, create_user_entry
from libldap import LDAP, LDAPControl, LDAPError
from libldap.constants import (
        LDAP_CONTROL_PASSWORDPOLICYREQUEST,
        LDAP_CONTROL_RELAX,
        LDAP_SCOPE_SUB,
        LDAP_MOD_REPLACE,
        LDAP_MOD_DELETE,
        LDAP_OPT_X_TLS_CACERTFILE,
)


class LDAPBindTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_bind(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['auth_user'], self.env['auth_pw'])

    def test_bind_async(self):
        ld = LDAP(self.env['uri_389'])
        msgid = ld.bind(self.env['auth_user'], self.env['auth_pw'], async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 0)

    def test_bind_controls(self):
        ld = LDAP(self.env['uri_389'])
        c = LDAPControl()
        c.add_control(LDAP_CONTROL_PASSWORDPOLICYREQUEST)
        msgid = ld.bind(self.env['auth_user'],
                        self.env['auth_pw'],
                        controls=c,
                        async=True)
        result = ld.result(msgid, controls=c)
        self.assertIn('ppolicy_msg', result)

    def test_bind_error(self):
        with self.assertRaises(LDAPError):
            ld = LDAP(self.env['uri_389'])
            ld.bind(self.env['auth_user'], 'bad password')

    def test_bind_error_async(self):
        ld = LDAP(self.env['uri_389'])
        msgid = ld.bind(self.env['auth_user'], 'bad password', async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 49)


class LDAPSearchTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_search_base(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        self.assertEqual(len(ld.search(self.env['suffix'])), 1)

    def test_search_filter(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        r = ld.search(self.env['suffix'], LDAP_SCOPE_SUB, filter='cn=auth')
        self.assertEqual(len(r), 1)

    def test_search_attributes(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        r = ld.search(self.env['suffix'], LDAP_SCOPE_SUB, filter='cn=auth', attributes=['cn'])
        self.assertIn('cn', r[0])
        self.assertNotIn('objectClass', r[0])

    def test_search_attributes_attrs_only(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        r = ld.search(self.env['suffix'], LDAP_SCOPE_SUB, filter='cn=auth', attrsonly=True)
        self.assertEqual(len(r[0]['cn']), 0)

    def test_search_sizelimit(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        with self.assertRaises(LDAPError) as cm:
            ld.search(self.env['suffix'], LDAP_SCOPE_SUB, sizelimit=1)
        self.assertEqual(cm.exception.return_code, 4)  # Size limit exceeded (4)

    def test_paged_search(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        gen = ld.paged_search(self.env['suffix'], LDAP_SCOPE_SUB, pagesize=1)
        self.assertIsInstance(gen, GeneratorType)
        [x for x in gen]


class LDAPAddTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]
        (dn, attributes) = create_user_entry()
        self.new_user_dn = dn
        self.new_user_attributes = attributes

    def tearDown(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        ld.delete(self.new_user_dn)

    def test_add(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        ld.add(self.new_user_dn, self.new_user_attributes)

    def test_add_async(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        msgid = ld.add(self.new_user_dn, self.new_user_attributes, async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 0)

    def test_add_with_relax(self):
        (dn, attributes) = create_user_entry(relax=True)
        self.new_user_dn = dn
        self.new_user_attributes = attributes
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        c = LDAPControl()
        c.add_control(LDAP_CONTROL_RELAX)
        ld.add(self.new_user_dn, self.new_user_attributes, controls=c)


class LDAPModifyTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_modify(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        dtime = datetime.utcnow().strftime('%Y%m%d%H%M%S.%fZ')
        changes = [
            ('description', ['Modified at %s' % (dtime,)], LDAP_MOD_REPLACE)
        ]
        ld.modify(self.env['target_user'], changes)

    def test_modify_mod_delete(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        changes = [('description', [], LDAP_MOD_DELETE)]
        ld.modify(self.env['target_user'], changes)

    def test_modify_async(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        dtime = datetime.utcnow().strftime('%Y%m%d%H%M%S.%fZ')
        changes = [
            ('description', ['Modified at %s' % (dtime,)], LDAP_MOD_REPLACE)
        ]
        msgid = ld.modify(self.env['target_user'], changes, async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 0)

    def test_modify_with_relax(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        c = LDAPControl()
        c.add_control(LDAP_CONTROL_RELAX)
        dtime = datetime.utcnow().strftime('%Y%m%d%H%M%S.%fZ')
        changes = [
            ('pwdAccountLockedTime', [dtime], LDAP_MOD_REPLACE)
        ]
        ld.modify(self.env['target_user'], changes, controls=c)


class LDAPDeleteTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        (dn, attributes) = create_user_entry()
        self.old_user_dn = dn
        self.old_user_attributes = attributes
        ld.add(self.old_user_dn, self.old_user_attributes)

    def test_delete(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        ld.delete(self.old_user_dn)

    def test_delete_async(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        msgid = ld.delete(self.old_user_dn, async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 0)


class LDAPRenameTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_rename(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        (newrdn, newparent) = self.env['target_user'].split(',', 1)
        newrdn += '-newrdn'
        ld.rename(self.env['target_user'], newrdn, newparent)
        # re-rename
        ld.rename('%s,%s' % (newrdn, newparent), self.env['target_user'].split(',', 1)[0], newparent)

    def test_rename_async(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        (newrdn, newparent) = self.env['target_user'].split(',', 1)
        newrdn += '-newrdn'
        msgid = ld.rename(self.env['target_user'], newrdn, newparent, async=True)
        result = ld.result(msgid)
        self.assertEqual(result['return_code'], 0)
        # re-rename
        ld.rename('%s,%s' % (newrdn, newparent), self.env['target_user'].split(',', 1)[0], newparent)

    def test_rename_oldrdn(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        (newrdn, newparent) = self.env['target_user'].split(',', 1)
        newrdn += '-newrdn'
        ld.rename(self.env['target_user'], newrdn, newparent, deleteoldrdn=False, async=True)
        time.sleep(0.3)
        entry = ld.search('%s,%s' % (newrdn, newparent), attributes=['uid'])[0]
        self.assertEqual(len(entry['uid']), 2)
        # re-rename
        ld.rename('%s,%s' % (newrdn, newparent), self.env['target_user'].split(',', 1)[0], newparent)

    def test_rename_without_parent(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        (newrdn, newparent) = self.env['target_user'].split(',', 1)
        newrdn += '-newrdn'
        ld.rename(self.env['target_user'], newrdn)
        # re-rename
        ld.rename('%s,%s' % (newrdn, newparent), self.env['target_user'].split(',', 1)[0], newparent)


class LDAPCompareTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]
        self.compare_attribute = 'description'
        self.compare_value = 'This value will be compared'
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        ld.modify(self.env['target_user'],
                  [(self.compare_attribute, [self.compare_value], LDAP_MOD_REPLACE)])

    def test_compare(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        result = ld.compare(self.env['target_user'], self.compare_attribute, self.compare_value)
        self.assertTrue(result)

    def test_compare_fail(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['root_dn'], self.env['root_pw'])
        result = ld.compare(self.env['target_user'], self.compare_attribute, 'dummy')
        self.assertFalse(result)


class LDAPWhoAmITests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_whoami(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['auth_user'], self.env['auth_pw'])
        result = ld.whoami()
        self.assertEqual('dn:' + self.env['auth_user'], result)


class LDAPPasswdTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_passwd(self):
        ld = LDAP(self.env['uri_389'])
        ld.bind(self.env['auth_user'], self.env['auth_pw'])
        newpassword = 'NewPassword'
        ld.passwd(self.env['auth_user'], self.env['auth_pw'], newpassword)
        ld.bind(self.env['auth_user'], newpassword)
        # re-passwd
        ld.passwd(self.env['auth_user'], newpassword, self.env['auth_pw'])
        ld.bind(self.env['auth_user'], self.env['auth_pw'])


class LDAPTlsTests(unittest.TestCase):
    def setUp(self):
        server = os.environ.get('TEST_SERVER', 'ldap-server')
        self.env = Environment[server]

    def test_tls_bind(self):
        ld = LDAP(self.env['uri_636'])
        ld.set_option(LDAP_OPT_X_TLS_CACERTFILE, str(cacert_file), is_global=True)
        ld.bind(self.env['auth_user'], self.env['auth_pw'])

    def test_start_tls_bind(self):
        ld = LDAP(self.env['uri_389'])
        ld.set_option(LDAP_OPT_X_TLS_CACERTFILE, str(cacert_file), is_global=True)
        ld.start_tls()
        ld.bind(self.env['auth_user'], self.env['auth_pw'])
