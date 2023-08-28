import unittest
from unittest.mock import Mock,patch, MagicMock
import ddt
from cinder.volume.drivers.ixsystems.common import TrueNASCommon
from cinder.volume import configuration as conf

@ddt.ddt
class TrueNASCommonTestCase(unittest.TestCase):

    def setUp(self):
        CONF = Mock(spec=conf.Configuration)
        CONF.iscsi_helper = 'tgtadm'
        CONF.volume_dd_blocksize = 512
        CONF.volume_driver = 'cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver'
        CONF.ixsystems_login = 'root'
        CONF.ixsystems_password = 'Pa55w0rd'
        CONF.ixsystems_apikey = ''
        CONF.ixsystems_server_hostname = '10.3.1.81'
        CONF.ixsystems_server_port = 80
        CONF.ixsystems_transport_type = 'http'
        CONF.ixsystems_volume_backend_name = 'iXsystems_FREENAS_Storage'
        CONF.ixsystems_iqn_prefix = 'iqn.2005-10.org.freenas.ctl'
        CONF.ixsystems_datastore_pool = 'cinder-zpool'
        CONF.ixsystems_dataset_path = 'cinder-zpool/mydataset'
        CONF.ixsystems_vendor_name = 'iXsystems'
        CONF.ixsystems_storage_protocol = 'iscsi'
        CONF.ixsystems_server_iscsi_port = 3260
        CONF.ixsystems_api_version = 'v2.0'
        CONF.ixsystems_reserved_percentage = 0
        self.common = TrueNASCommon(configuration=CONF)
        self.common.do_custom_setup()

    def test_check_flags(self):
        self.assertIsNone(self.common.check_flags())
        
    def test_do_custom_setup(self):
        self.assertIsNone(self.common.do_custom_setup())

    @ddt.data(("vol1",1,"/pool/dataset",b'{"name": "cinder-zpool/mydataset/vol1", "type": "VOLUME", "volsize": 1073741824}'
               ))
    @ddt.unpack
    def test_create_volume(self,volname,volsize, request_d,urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.create_volume(volname,volsize)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)
                self.assertEqual(mock_request.method_calls[0][1][1],urlreadresult)

    @ddt.data(("target-6410a089",
               b'[{"id":2,"name":"target-6410a089","alias":null,"mode":"ISCSI","groups":[{"portal":1,"initiator":1,"auth":null,"authmethod":"NONE"}]}]',
               2))
    @ddt.unpack
    def test_get_iscsitarget_id(self,name, urlreadresult,expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.assertEqual(self.common.get_iscsitarget_id(name), expected)

    @ddt.data(("target-6410a089",
               b'[{"id":2,"name":"target-6410a089","serial":"000c29aef785001","type":"DISK","path":"zvol/pool/cinder/volume-6410a089","filesize":"0","blocksize":512,"pblocksize":false,"avail_threshold":null,"comment":"","naa":"0x6589cfc00000033f74d0d84613b0caea","insecure_tpc":true,"xen":false,"rpm":"SSD","ro":false,"enabled":true,"vendor":"TrueNAS","disk":"zvol/pool/cinder/volume-6410a089","locked":false}]',
               2))
    @ddt.unpack
    def test_get_extent_id(self,name, urlreadresult,expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.assertEqual(self.common.get_extent_id(name), expected)                            

    @ddt.data(("target-6410a089",
               b'[{"id":0,"lunid":0,"extent":2,"target":2}]',
               0))
    @ddt.unpack
    def test_get_tgt_ext_id(self,name, urlreadresult,expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.assertEqual(self.common.get_tgt_ext_id(name), expected)                

    @ddt.data(("target-6410a089", "target-6410a089",))
    @ddt.unpack
    def test_create_iscsitarget(self,name, volume_name):
        self.common._create_target = MagicMock()
        self.common._create_extent = MagicMock()
        self.common._target_to_extent = MagicMock()
        self.assertIsNone(self.common.create_iscsitarget(name, volume_name))
        self.common._create_target.assert_called_once()
        self.common._create_extent.assert_called_once()
        self.common._target_to_extent.assert_called_once()

    @ddt.data(("12",
               "/iscsi/target/id/12",
              b'true'))
    @ddt.unpack
    def test_delete_target(self,targetid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.delete_target(targetid)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("12",
               "/iscsi/extent/id/12",
              b'true'))
    @ddt.unpack
    def test_delete_extent(self,targetid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.delete_extent(targetid)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("volume-9e9ab808",
               "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume-9e9ab808",
              b'true'))
    @ddt.unpack
    def test_delete_volume(self,name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common._dependent_clone = MagicMock(return_value=False)
                self.common.delete_volume(name)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)                                

    @ddt.data(("snap-8b839f49",
               "volume-cf879408",
               "/zfs/snapshot",
              b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49","name":"pool/cinder/volume-cf879408@snap-8b839f49","pool":"pool","type":"SNAPSHOT"}'))
    @ddt.unpack
    def test_create_snapshot(self,name,volume_name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.create_snapshot(name,volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("snap-8b839f49",
               "volume-cf879408",
               "/zfs/snapshot/id/cinder-zpool%2Fmydataset%2Fvolume-cf879408@snap-8b839f49",
              b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49","name":"pool/cinder/volume-cf879408@snap-8b839f49","pool":"pool","type":"SNAPSHOT"}'))
    @ddt.unpack
    def test_delete_snapshot(self,name,volume_name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.delete_snapshot(name,volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("volume-83b64291",
               "volume-be93bccd",
               "snap-79fe98cf",
               "/zfs/snapshot/clone",
              b'{"snapshot": "pool/cinder/volume-be93bccd@snap-79fe98cf", "dataset_dst": "pool/cinder/volume-83b64291"}'))
    @ddt.unpack
    def test_create_volume_from_snapshot(self, name, snapshot_name, snap_zvol_name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.create_volume_from_snapshot(name, snapshot_name, snap_zvol_name)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("volume-06b80325",
               "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume-06b80325/promote",
              b'null'))
    @ddt.unpack
    def test_promote_volume(self, volume_name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.promote_volume(volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("/system/version",
              b'"TrueNAS-12.0-U8.1"'))
    @ddt.unpack
    def test_system_version(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.system_version()
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("/tunable",
            b'[{"id":3,"value":"2","type":"LOADER","comment":"","enabled":true,"var":"hint.isp.0.role"},{"id":4,"value":"2","type":"LOADER","comment":"","enabled":true,"var":"hint.isp.1.role"},{"id":5,"value":"2","type":"LOADER","comment":"","enabled":true,"var":"hint.isp.2.role"},{"id":6,"value":"2","type":"LOADER","comment":"","enabled":true,"var":"hint.isp.3.role"},{"id":7,"value":"256","type":"LOADER","comment":"","enabled":true,"var":"kern.cam.ctl.max_ports"}]'))
    @ddt.unpack
    def test_tunable(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.tunable()
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("/pool/dataset/id/cinder-zpool%2Fmydataset",
            b'{"id":"pool/cinder","name":"pool/cinder","pool":"pool","used":{"value":"4.26G","rawvalue":"4570963968","parsed":4570963968,"source":"NONE"},"available":{"value":"48.9G","rawvalue":"52530008064","parsed":52530008064,"source":"NONE"}}'))
    @ddt.unpack
    def test_update_volume_stats(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.system_version = MagicMock(return_value = "TrueNAS")
                self.common.update_volume_stats()
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)

    @ddt.data(("volume-f9ecfc53", 2,
        "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume-f9ecfc53",
        b'{"id":"cinder-zpool/mydataset/volume-f9ecfc53","name":"cinder-zpool/mydataset/volume-f9ecfc53","pool":"pool","type":"VOLUME","volsize":{"value":"2G","rawvalue":"2147483648","parsed":2147483648,"source":"LOCAL"},"used":{"value":"2.06G","rawvalue":"2216689664","parsed":2216689664,"source":"NONE"},"available":{"value":"50.0G","rawvalue":"53639102464","parsed":53639102464,"source":"NONE"}}'))
    @ddt.unpack    
    def test_extend_volume(self, name, new_size, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request') as mock_request:
            with patch('cinder.volume.drivers.ixsystems.freenasapi.urllib.request.urlopen',return_value =urlrespond) as mock_urlopen:
                self.common.extend_volume(name, new_size)
                self.assertEqual(mock_request.method_calls[0][1][0],self.common.handle.get_url()+request_d)        

    @ddt.data(("f9ecfc53-2b12-4bfb-abe1-694970cc1341",
               "10.3.1.81:3260,target-2b12 iqn.2005-10.org.freenas.ctltarget-2b12"))
    @ddt.unpack
    def test_create_export(self, volume_name, expected):
        handle = self.common.create_export(volume_name)
        self.assertEqual(handle , expected)

if __name__ == '__main__':
    unittest.main()