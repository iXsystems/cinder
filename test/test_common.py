import unittest
from unittest.mock import Mock, patch, MagicMock
import ddt
from cinder.volume.drivers.ixsystems.common import TrueNASCommon
from cinder.volume import configuration as conf

request_patch = 'cinder.volume.drivers.ixsystems.freenasapi.urllib.request'
open_patch = 'cinder.volume.drivers.ixsystems.'\
    'freenasapi.urllib.request.urlopen'


@ddt.ddt
class TrueNASCommonTestCase(unittest.TestCase):

    def setUp(self):
        CONF = Mock(spec=conf.Configuration)
        for k, v in fake_config_dict.items():
            setattr(CONF, k, v)
        self.common = TrueNASCommon(configuration=CONF)
        self.common.do_custom_setup()

    def test_check_flags(self):
        self.assertIsNone(self.common.check_flags())

    def test_do_custom_setup(self):
        self.assertIsNone(self.common.do_custom_setup())

    @ddt.data(("vol1", 1, "/pool/dataset",
               b'{"name": "cinder-zpool/mydataset/vol1", '
               b'"type": "VOLUME", "volsize": 1073741824}'
               ))
    @ddt.unpack
    def test_create_volume(self, volname, volsize, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.create_volume(volname, volsize)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)
                self.assertEqual(mock_request.method_calls[0][1][1],
                                 urlreadresult)

    @ddt.data(("target-6410a089",
               b'[{"id":2,"name":"target-6410a089","alias":null,"mode":'
               b'"ISCSI","groups":[{"portal":1,"initiator":1,"auth":nul'
               b'l,"authmethod":"NONE"}]}]', 2))
    @ddt.unpack
    def test_get_iscsitarget_id(self, name, urlreadresult, expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.assertEqual(self.common.get_iscsitarget_id(name),
                                 expected)

    @ddt.data(("target-6410a089",
               b'[{"id":2,"name":"target-6410a089","serial":"000c29aef7850'
               b'01","type":"DISK","path":"zvol/pool/cinder/volume-6410a08'
               b'9","filesize":"0","blocksize":512,"pblocksize":false,"ava'
               b'il_threshold":null,"comment":"","naa":"0x6589cfc00000033f'
               b'74d0d84613b0caea","insecure_tpc":true,"xen":false,"rpm":"'
               b'SSD","ro":false,"enabled":true,"vendor":"TrueNAS","disk":'
               b'"zvol/pool/cinder/volume-6410a089","locked":false}]', 2))
    @ddt.unpack
    def test_get_extent_id(self, name, urlreadresult, expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.assertEqual(self.common.get_extent_id(name), expected)

    @ddt.data(("target-6410a089",
               b'[{"id":0,"lunid":0,"extent":2,"target":2}]',
               0))
    @ddt.unpack
    def test_get_tgt_ext_id(self, name, urlreadresult, expected):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.assertEqual(self.common.get_tgt_ext_id(name), expected)

    @ddt.data(("target-6410a089", "target-6410a089",))
    @ddt.unpack
    def test_create_iscsitarget(self, name, volume_name):
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
    def test_delete_target(self, targetid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_target(targetid)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("12",
               "/iscsi/extent/id/12",
              b'true'))
    @ddt.unpack
    def test_delete_extent(self, targetid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_extent(targetid)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("volume-9e9ab808",
               "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume-9e9ab808",
              b'true'))
    @ddt.unpack
    def test_delete_volume(self, name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common._dependent_clone = MagicMock(return_value=False)
                self.common.delete_volume(name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("snap-8b839f49",
               "volume-cf879408",
               "/zfs/snapshot",
              b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49","name":'
               b'"pool/cinder/volume-cf879408@snap-8b839f49","pool":"pool"'
               b',"type":"SNAPSHOT"}'))
    @ddt.unpack
    def test_create_snapshot(self, name, volume_name,
                             request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.create_snapshot(name, volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("snap-8b839f49",
               "volume-cf879408",
               "/zfs/snapshot/id/cinder-zpool%2Fmydataset%2Fvolume-cf879408"
               "@snap-8b839f49",
              b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49","name":'
               b'"pool/cinder/volume-cf879408@snap-8b839f49","pool":"pool"'
               b',"type":"SNAPSHOT"}'))
    @ddt.unpack
    def test_delete_snapshot(self, name, volume_name,
                             request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_snapshot(name, volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("volume-83b64291",
               "volume-be93bccd",
               "snap-79fe98cf",
               "/zfs/snapshot/clone",
              b'{"snapshot": "pool/cinder/volume-be93bccd@snap-79fe98cf"'
               b', "dataset_dst": "pool/cinder/volume-83b64291"}'))
    @ddt.unpack
    def test_create_volume_from_snapshot(self, name, snapshot_name,
                                         snap_zvol_name, request_d,
                                         urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.create_volume_from_snapshot(name, snapshot_name,
                                                        snap_zvol_name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("volume-06b80325",
               "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume"
               "-06b80325/promote",
              b'null'))
    @ddt.unpack
    def test_promote_volume(self, volume_name, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.promote_volume(volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("/system/version",
              b'"TrueNAS-12.0-U8.1"'))
    @ddt.unpack
    def test_system_version(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.system_version()
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("/tunable",
               b'[{"id":3,"value":"2","type":"LOADER","comment":"","enabled":'
               b'true,"var":"hint.isp.0.role"},{"id":4,"value":"2","type":"LO'
               b'ADER","comment":"","enabled":true,"var":"hint.isp.1.role"},{'
               b'"id":5,"value":"2","type":"LOADER","comment":"","enabled":tr'
               b'ue,"var":"hint.isp.2.role"},{"id":6,"value":"2","type":"LOAD'
               b'ER","comment":"","enabled":true,"var":"hint.isp.3.role"},{"i'
               b'd":7,"value":"256","type":"LOADER","comment":"","enabled":tr'
               b'ue,"var":"kern.cam.ctl.max_ports"}]'))
    @ddt.unpack
    def test_tunable(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.tunable()
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("/pool/dataset/id/cinder-zpool%2Fmydataset",
               b'{"id":"pool/cinder","name":"pool/cinder","pool":"pool"'
               b',"used":{"value":"4.26G","rawvalue":"4570963968","pars'
               b'ed":4570963968,"source":"NONE"},"available":{"value":"'
               b'48.9G","rawvalue":"52530008064","parsed":52530008064,"'
               b'source":"NONE"}}'))
    @ddt.unpack
    def test_update_volume_stats(self, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.system_version = MagicMock(return_value="TrueNAS")
                self.common.update_volume_stats()
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("volume-f9ecfc53", 2,
               "/pool/dataset/id/cinder-zpool%2Fmydataset%2Fvolume-f9ecfc53",
               b'{"id":"cinder-zpool/mydataset/volume-f9ecfc53","name":"cind'
               b'er-zpool/mydataset/volume-f9ecfc53","pool":"pool","type":"V'
               b'OLUME","volsize":{"value":"2G","rawvalue":"2147483648","par'
               b'sed":2147483648,"source":"LOCAL"},"used":{"value":"2.06G",'
               b'"rawvalue":"2216689664","parsed":2216689664,"source":"NONE'
               b'"},"available":{"value":"50.0G","rawvalue":"53639102464","'
               b'parsed":53639102464,"source":"NONE"}}'))
    @ddt.unpack
    def test_extend_volume(self, name, new_size, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.extend_volume(name, new_size)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("volume-ba323557", "snap-ba323557", "volume-e66d45cd",
               "/replication/",
               b'{ "id": 1, "target_dataset": "pool/cinder/volume-ba323557'
               b'", "recursive": false, "compression": null, "speed_limi'
               b't": null, "enabled": true, "direction": "PUSH", "transp'
               b'ort": "LOCAL", "netcat_active_side": null, "netcat_active'
               b'_side_port_min": null, "netcat_active_side_port_max": null,'
               b' "source_datasets": [  "pool/cinder/volume-e66d45cd" ],'
               b' "exclude": [], "naming_schema": [], "auto": true, "o'
               b'nly_matching_schedule": true, "readonly": "IGNORE", "allo'
               b'w_from_scratch": false, "hold_pending_snapshots": false, '
               b'"retention_policy": "SOURCE", "lifetime_unit": null, "lif'
               b'etime_value": null, "large_block": true, "embed": false,'
               b' "compressed": true, "retries": 5, "netcat_active_side'
               b'_listen_address": null, "netcat_passive_side_connect_addre'
               b'ss": null, "logging_level": null, "name": "Create volume'
               b'volume-ba323557 from volume-e66d45cd@snap-ba323557", "stat'
               b'e": {  "state": "FINISHED" }, "properties": true, "pr'
               b'operties_exclude": [], "replicate": false, "encryption":'
               b'false, "encryption_key": null, "encryption_key_format": '
               b'null, "encryption_key_location": null, "ssh_credentials"'
               b': null, "periodic_snapshot_tasks": [], "also_include_na'
               b'ming_schema": [  "snap-ba323557-%Y-%m-%d-%H-%M" ], "sc'
               b'hedule": {  "minute": "*",  "hour": "*",  "dom": "*",'
               b'"month": "*",  "dow": "*",  "begin": "00:00",  "end": '
               b'"23:59" }, "restrict_schedule": null, "job": null}',
               {"id": 1,"state": {  "state": "FINISHED" }}
               ))
    @ddt.unpack
    def test_replicate_volume_from_snapshot(self, target_volume_name,
                                            snapshot_name, src_volume_name,
                                            request_d, urlreadresult,
                                            replicationstatresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        self.common.replication_run = MagicMock()
        self.common.replication_stats = MagicMock(return_value
                                                  = replicationstatresult)
        self.common.delete_snapshot = MagicMock()
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.replicate_volume_from_snapshot(target_volume_name,
                                                           snapshot_name,
                                                           src_volume_name)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("1", "/replication/id/1",
               b'{ "id": 1, "target_dataset": "pool/cinder/volume-ba323557",'
               b'"state": {"state": "FINISHED"}}'))
    @ddt.unpack
    def test_replication_stats(self, repid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.replication_stats(repid)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("1", "/replication/id/1",
               b'{ "id": 1, "target_dataset": "pool/cinder/volume-ba323557",'
               b'true'))
    @ddt.unpack
    def test_replication_delete(self, repid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.replication_delete(repid)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("1", "/replication/id/1/run",
               b'217682'))
    @ddt.unpack
    def test_replication_run(self, repid, request_d, urlreadresult):
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch) as mock_request:
            with patch(open_patch, return_value=urlrespond):
                self.common.replication_run(repid)
                self.assertEqual(mock_request.method_calls[0][1][0],
                                 self.common.handle.get_url()+request_d)

    @ddt.data(("f9ecfc53-2b12-4bfb-abe1-694970cc1341",
               "10.3.1.81:3260,target-2b12 iqn.2005-10.org."
               "freenas.ctltarget-2b12"))
    @ddt.unpack
    def test_create_export(self, volume_name, expected):
        handle = self.common.create_export(volume_name)
        self.assertEqual(handle, expected)


fake_config_dict = {
    'iscsi_helper': 'tgtadm',
    'volume_dd_blocksize': 512,
    'volume_driver':
        'cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver',
    'ixsystems_login': 'root',
    'ixsystems_password': 'Pa55w0rd',
    'ixsystems_apikey': '',
    'ixsystems_server_hostname': '10.3.1.81',
    'ixsystems_server_port': 80,
    'ixsystems_transport_type': 'http',
    'ixsystems_volume_backend_name': 'iXsystems_FREENAS_Storage',
    'ixsystems_iqn_prefix': 'iqn.2005-10.org.freenas.ctl',
    'ixsystems_datastore_pool': 'cinder-zpool',
    'ixsystems_dataset_path': 'cinder-zpool/mydataset',
    'ixsystems_vendor_name': 'iXsystems',
    'ixsystems_storage_protocol': 'iscsi',
    'ixsystems_server_iscsi_port': 3260,
    'ixsystems_api_version': 'v2.0',
    'ixsystems_reserved_percentage': 0,
    'ixsystems_replication_timetout' : 600
    }


if __name__ == '__main__':
    unittest.main()
