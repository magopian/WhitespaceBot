#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
import unittest
import robot
from os import remove
from string import rstrip


class TestUsers(unittest.TestCase):
    old_users_file = 'test_old_users.txt'
    new_users_file = 'test_new_users.txt'
    old_users = ['john ', 'ray  ', 'pete   ']
    new_users = ['john ', 'ray  ', 'pete   ', 'mat    ']

    def setUp(self):
        """Create old and new users files"""
        with open(self.old_users_file, 'w') as f:
            f.write('\n'.join(self.old_users))
            f.write('\n')
        with open(self.new_users_file, 'w') as f:
            f.write('\n'.join(self.new_users))

    def tearDown(self):
        """Delete test old and new users files"""
        remove(self.old_users_file)
        remove(self.new_users_file)

    def test_old_users_list(self):
        old_users_list = robot.load_user_list(self.old_users_file)
        old_users = map(rstrip, self.old_users)
        self.assertEqual(old_users_list, old_users)

    def test_new_users_list(self):
        new_users_list = robot.load_user_list(self.new_users_file)
        new_users = map(rstrip, self.new_users)
        self.assertEqual(new_users_list, new_users)

    def test_get_user(self):
        user = robot.get_user(self.new_users_file, self.old_users_file)
        new_users = map(rstrip, self.new_users)
        self.assertIn(user, new_users)

    def test_save_user(self):
        robot.save_user(self.old_users_file, 'mat')
        old_users_list = robot.load_user_list(self.old_users_file)
        self.assertIn('mat', old_users_list)


if __name__ == '__main__':
    unittest.main()
