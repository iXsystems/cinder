import unittest
from unittest.mock import patch, MagicMock
import ddt
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer

request_patch = 'cinder.volume.drivers.ixsystems.freenasapi.urllib.request'
open_patch = 'cinder.volume.drivers.ixsystems.'\
    'freenasapi.urllib.request.urlopen'


@ddt.ddt
class FreeNasServerTestCase(unittest.TestCase):

    def setUp(self):
        self.freeNasServer = FreeNASServer("host", "80",
                                           "root", "password",
                                           "", "v2.0", "http")

    @ddt.data(("select", "GET"),
              ("create", "POST"),
              ("update", "PUT"),
              ("delete", "DELETE"),
              ("", None))
    @ddt.unpack
    def test_get_method(self, command_d, expected):
        self.assertEqual(expected, self.freeNasServer._get_method(command_d))

    @ddt.data(("host"))
    def test_get_host(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_host())

    @ddt.data(("80"))
    def test_get_port(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_port())

    @ddt.data(("root"))
    def test_get_username(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_username())

    @ddt.data(("password"))
    def test_get_password(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_password())

    @ddt.data(("http"))
    def test_get_transport_type(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_transport_type())

    @ddt.data(("http://host/api/v2.0"))
    def test_get_url(self, expected):
        self.assertEqual(expected, self.freeNasServer.get_url())

    @ddt.data(("host", "host"))
    @ddt.unpack
    def test_set_host(self, input, expected):
        self.freeNasServer.set_host(input)
        self.assertEqual(expected, self.freeNasServer.get_host())

    @ddt.data(("80", "80"))
    @ddt.unpack
    def test_set_port(self, input, expected):
        self.freeNasServer.set_port(input)
        self.assertEqual(expected, self.freeNasServer.get_port())

    @ddt.data(("root", "root"))
    @ddt.unpack
    def test_set_username(self, input, expected):
        self.freeNasServer.set_username(input)
        self.assertEqual(expected, self.freeNasServer.get_username())

    @ddt.data(("password", "password"))
    @ddt.unpack
    def test_set_password(self, input, expected):
        self.freeNasServer.set_password(input)
        self.assertEqual(expected, self.freeNasServer.get_password())

    @ddt.data(("http", "http"))
    @ddt.unpack
    def test_set_transport_type(self, input, expected):
        self.freeNasServer.set_transport_type(input)
        self.assertEqual(expected, self.freeNasServer.get_transport_type())

    @ddt.data(("select", "/system/version", None, '"TrueNAS-12.0-U8.1"',
               {"status": "ok", "response": "\"TrueNAS-12.0-U8.1\"",
                "code": -1}),
              ("select", "/pool/dataset/id/pool%2Fcinder", None,
               '{ "id": 12, "name": "target-8cf1022d" }',
               {"status": "ok", "response": "{ \"id\": 12, \"name\": \"ta"
                "rget-8cf1022d\" }", "code": -1}))
    @ddt.unpack
    def test_invoke_command(self, command_d, request_d, param_list,
                            urlread, expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlread
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.assertEqual(expected, self.freeNasServer.invoke_command
                                 (command_d, request_d, param_list))


if __name__ == '__main__':
    unittest.main()
