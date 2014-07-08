# -*- coding: utf-8 -*-

import app
import unittest

class TestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()
    
    def tearDown(self):
        pass

    def check(self, url, inkeys, notkeys):
        rv = self.app.get(url, follow_redirects=True)
        for key in inkeys:
            assert key in rv.data
        for key in notkeys:
            assert key not in rv.data

    def test_request(self):
        test_data = [ ['/',               ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']],
                      ['/channel/',       ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']],
                      ['/channel/stable', ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']],
                      ['/channel/beta',   ['<h4>beta</h4>',   '.exe'], ['<h4>stable</h4>', '<h4>dev']],
                      ['/channel/dev',    ['<h4>dev</h4>',    '.exe'], ['<h4>stable</h4>', '<h4>beta</h4>']],
                      ['/channel/null',   ['<h4>stable</h4>', '.exe'], ['<h4>beta</h4>', '<h4>dev']],
					  ['/channel/all',    ['<h4>stable</h4>', '<h4>beta</h4>', '<h4>dev', '.exe'], []]]
        for data in test_data:
            self.check(data[0], data[1], data[2])

if __name__ == '__main__':
    unittest.main()

