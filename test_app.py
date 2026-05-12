# -*- coding: utf-8 -*-

from collections import OrderedDict
import unittest

from get_chrome.cache import TTLCache
from get_chrome.config import Config
from get_chrome.google_update import ChromeUpdateError, GoogleUpdateClient, parse_installer_urls
from get_chrome.service import ChromeInstallerService
from get_chrome.web import create_app


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


class RecordingOpener:
    def __init__(self):
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return FakeResponse()


def make_service(opener=None):
    opener = opener or RecordingOpener()
    client = GoogleUpdateClient('https://example.test/update', 7, opener=opener)
    payloads = OrderedDict((channel, f'<request>{channel}</request>'.encode('utf-8'))
                           for channel in ('stable', 'beta', 'dev'))
    cache = TTLCache[list[str]](60)
    return ChromeInstallerService(client, payloads, cache), opener


class ConfigTest(unittest.TestCase):
    def test_config_from_env_overrides_defaults(self):
        config = Config.from_env({
            'GOOGLE_UPDATE_URL': 'https://example.test/update',
            'CACHE_TTL_SECONDS': '120',
            'URL_TIMEOUT_SECONDS': '10',
            'PORT': '8080',
        })

        self.assertEqual(config.google_update_url, 'https://example.test/update')
        self.assertEqual(config.cache_ttl_seconds, 120)
        self.assertEqual(config.url_timeout_seconds, 10)
        self.assertEqual(config.port, 8080)

    def test_config_rejects_invalid_ints(self):
        with self.assertRaises(ValueError):
            Config.from_env({'CACHE_TTL_SECONDS': '0'})


class ParserTest(unittest.TestCase):
    def test_parse_installer_urls(self):
        self.assertEqual(
            parse_installer_urls(RESPONSE_XML),
            ['https://dl.google.com/chrome/test/chrome_installer.exe'],
        )

    def test_parse_installer_urls_requires_package(self):
        with self.assertRaises(ChromeUpdateError):
            parse_installer_urls(b'<response><app><updatecheck status="noupdate" /></app></response>')

    def test_parse_installer_urls_wraps_invalid_xml(self):
        with self.assertRaises(ChromeUpdateError):
            parse_installer_urls(b'not xml')


class ServiceTest(unittest.TestCase):
    def test_service_returns_selected_channel_urls(self):
        service, opener = make_service()

        links = service.installer_urls_for('beta')

        self.assertEqual(list(links.keys()), ['beta'])
        self.assertEqual(links['beta'], ['https://dl.google.com/chrome/test/chrome_installer.exe'])
        self.assertEqual(len(opener.calls), 1)
        self.assertEqual(opener.calls[0][1], 7)

    def test_service_returns_all_channels_in_order(self):
        service, _opener = make_service()

        links = service.installer_urls_for('all')

        self.assertEqual(list(links.keys()), ['stable', 'beta', 'dev'])

    def test_service_uses_cache(self):
        service, opener = make_service()

        service.installer_urls_for('stable')
        service.installer_urls_for('stable')

        self.assertEqual(len(opener.calls), 1)

    def test_service_returns_no_links_for_invalid_channel(self):
        service, _opener = make_service()

        self.assertEqual(service.installer_urls_for('unknown'), OrderedDict())


class WebTest(unittest.TestCase):
    def setUp(self):
        self.service, _opener = make_service()
        self.client = create_app(Config(), service=self.service).test_client()

    def assert_contains(self, url, inkeys, notkeys):
        response = self.client.get(url, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        body = response.data.decode('utf-8')
        for key in inkeys:
            self.assertIn(key, body)
        for key in notkeys:
            self.assertNotIn(key, body)

    def test_routes_render_expected_channels(self):
        test_data = [('/', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/stable', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/beta', ['<h4>beta</h4>', '.exe'], ['<h4>stable</h4>', '<h4>dev']),
                     ('/channel/dev', ['<h4>dev</h4>', '.exe'], ['<h4>stable</h4>', '<h4>beta</h4>']),
                     ('/channel/null', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']),
                     ('/channel/all', ['<h4>stable</h4>', '<h4>beta</h4>', '<h4>dev</h4>', '.exe'], [])]
        for data in test_data:
            with self.subTest(url=data[0]):
                self.assert_contains(data[0], data[1], data[2])

    def test_chrome_update_errors_render_bad_gateway(self):
        class FailingService:
            def installer_urls_for(self, _channel):
                raise ChromeUpdateError('boom')

        client = create_app(Config(), service=FailingService()).test_client()

        response = client.get('/channel/stable')

        self.assertEqual(response.status_code, 502)
        self.assertIn('Unable to load Chrome installer URLs', response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
