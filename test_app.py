# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

import app


RESPONSE_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<response protocol="3.0" server="prod">
  <app appid="{8A69D345-D564-463C-AFF1-A69D9E530F96}" status="ok">
    <updatecheck status="ok">
      <urls>
        <url codebase="https://dl.google.com/chrome/test/"/>
      </urls>
      <manifest version="1.2.3.4">
        <packages>
          <package name="chrome_installer.exe" required="true"/>
        </packages>
      </manifest>
    </updatecheck>
  </app>
</response>'''


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return RESPONSE_XML


class TestCase(unittest.TestCase):

    def setUp(self):
        app.cache.clear()
        self.app = app.app.test_client()

    def check(self, url, inkeys, notkeys):
        rv = self.app.get(url, follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        body = rv.data.decode('utf-8')
        for key in inkeys:
            self.assertIn(key, body)
        for key in notkeys:
            self.assertNotIn(key, body)

    @patch('app.urlopen', return_value=FakeResponse())
    def test_request(self, _urlopen):
        test_data = [('/', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/stable', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/beta', ['<h4>beta</h4>', '.exe'], ['<h4>stable</h4>', '<h4>dev']),
                     ('/channel/dev', ['<h4>dev</h4>', '.exe'], ['<h4>stable</h4>', '<h4>beta</h4>']),
                     ('/channel/null', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/all', ['<h4>stable</h4>', '<h4>beta</h4>', '<h4>dev</h4>', '.exe'], [])]
        for data in test_data:
            with self.subTest(url=data[0]):
                self.check(data[0], data[1], data[2])

    def test_parse_installer_urls(self):
        self.assertEqual(
            app.parse_installer_urls(RESPONSE_XML),
            ['https://dl.google.com/chrome/test/chrome_installer.exe'],
        )

    def test_parse_installer_urls_requires_package(self):
        with self.assertRaises(app.ChromeUpdateError):
            app.parse_installer_urls(b'<response><app><updatecheck status="noupdate" /></app></response>')


if __name__ == '__main__':
    unittest.main()
