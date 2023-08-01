import unittest
import ddt

from cinder.volume.drivers.ixsystems import utils as ix_utils

@ddt.ddt
class UtilsTestCase(unittest.TestCase):
    
    @ddt.data((1024 * 1024 * 1024,1),(1.5*1024 * 1024 * 1024,1.5))
    @ddt.unpack
    def test_get_size_in_gb(self,size_in_bytes,expected):
        self.assertEqual(expected, ix_utils.get_size_in_gb(size_in_bytes))

    @ddt.data(("123456-123456-abcdef-abcdef-abcdef","iqn","volume-123456"),
              ("234567-234567-abcdef-abcdef-abcdef","iqn","volume-234567"))
    @ddt.unpack
    def test_generate_freenas_volume_name(self,name,iqn_prefix,expected):
        self.assertEqual(expected, ix_utils.generate_freenas_volume_name(name,iqn_prefix)['name'])

    @ddt.data(("123456-123456-abcdef-abcdef-abcdef","iqn","snap-123456"),
              ("234567-234567-abcdef-abcdef-abcdef","iqn","snap-234567"))
    @ddt.unpack
    def test_generate_freenas_snapshot_name(self,name, iqn_prefix,expected):
        self.assertEqual(expected, ix_utils.generate_freenas_snapshot_name(name,iqn_prefix)['name'])

    @ddt.data(("server1","3260","server1:3260"),
              ("server2","3261","server2:3261"))
    @ddt.unpack    
    def test_get_iscsi_portal(self,hostname, port,expected):
        self.assertEqual(expected, ix_utils.get_iscsi_portal(hostname,port))


    @ddt.data(("TrueNAS-12.0-U8.1",("TrueNAS","12.0","U8.1")),
              ("",('VersionNotFound', '0', '')))
    @ddt.unpack    
    def test_parse_truenas_version(self,version,expected):
        self.assertEqual(expected, ix_utils.parse_truenas_version(version))

if __name__ == '__main__':
    unittest.main()