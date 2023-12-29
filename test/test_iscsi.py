import unittest
from unittest.mock import Mock, patch, MagicMock
import ddt
from cinder.volume.drivers.ixsystems.common import TrueNASCommon
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer
from cinder.volume.drivers.ixsystems.iscsi import FreeNASISCSIDriver
from cinder.volume import configuration as conf
from cinder.tests.unit import fake_volume
from cinder import context

request_patch = 'cinder.volume.drivers.ixsystems.freenasapi.urllib.request'
open_patch = 'cinder.volume.drivers.ixsystems.'\
    'freenasapi.urllib.request.urlopen'


class fakecommon(TrueNASCommon):

    def __init__(self, configuration=None):
        CONF = MagicMock(spec=conf.Configuration)
        for k, v in fake_config_dict.items():
            setattr(CONF, k, v)
        self.is_service_project = MagicMock(return_value=False)
        self.common = TrueNASCommon(configuration=CONF)
        self.common.do_custom_setup()
        self.common._create_target = MagicMock()
        self.common._create_extent = MagicMock()
        self.common._target_to_extent = MagicMock()
        self.common._dependent_clone = MagicMock()
        self.common.delete_iscsitarget = MagicMock()
        self.common.replicate_volume_from_snapshot = MagicMock()
        super().__init__(configuration=CONF)

    def _create_handle(self, **kwargs):
        """Instantiate client for API comms with iXsystems FREENAS server."""
        host_system = kwargs['hostname']
        self.handle = FreeNASServer(
            host=host_system,
            port=kwargs['port'],
            username=kwargs['login'],
            password=kwargs['password'],
            apikey=kwargs['apikey'],
            api_version=kwargs['api_version'],
            transport_type=kwargs['transport_type'])

    def create_volume(self, name, size):
        urlreadresult = b'{"name": "cinder-zpool/mydataset/vol1", "type": '\
            b'"VOLUME", "volsize": 1073741824}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.create_volume(name, size)

    def get_iscsitarget_id(self, name):
        urlreadresult = b'[{"id":2,"name":"target-6410a089","alias":null,'\
            b'"mode":"ISCSI","groups":[{"portal":1,"initiator":1,"auth":n'\
            b'ull,"authmethod":"NONE"}]}]'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.get_iscsitarget_id(name)

    def get_extent_id(self, name):
        urlreadresult = b'[{"id":2,"name":"target-6410a089","serial":"000'\
            b'c29aef785001","type":"DISK","path":"zvol/pool/cinder/volume'\
            b'-6410a089","filesize":"0","blocksize":512,"pblocksize":fals'\
            b'e,"avail_threshold":null,"comment":"","naa":"0x6589cfc00000'\
            b'033f74d0d84613b0caea","insecure_tpc":true,"xen":false,"rpm"'\
            b':"SSD","ro":false,"enabled":true,"vendor":"TrueNAS","disk":'\
            b'"zvol/pool/cinder/volume-6410a089","locked":false}]'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.get_extent_id(name)

    def get_tgt_ext_id(self, name):
        urlreadresult = b'[{"id":0,"lunid":0,"extent":2,"target":2}]'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.get_tgt_ext_id(name)

    def create_iscsitarget(self, name, volume_name):
        self.common.create_iscsitarget(name, volume_name)

    def delete_target(self, target_id):
        urlreadresult = b'true'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_target(target_id)

    def delete_extent(self, extent_id):
        urlreadresult = b'true'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_extent(extent_id)

    def delete_volume(self, name):
        urlreadresult = b'true'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common._dependent_clone = MagicMock(return_value=False)
                self.common.delete_volume(name)

    def create_snapshot(self, name, volume_name):
        urlreadresult = b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49"'\
            b',"name":"pool/cinder/volume-cf879408@snap-8b839f49","pool":"p'\
            b'ool","type":"SNAPSHOT"}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.create_snapshot(name, volume_name)

    def delete_snapshot(self, name, volume_name):
        urlreadresult = b'{"id":"pool/cinder/volume-cf879408@snap-8b839f49'\
            b'","name":"pool/cinder/volume-cf879408@snap-8b839f49","pool":'\
            b'"pool","type":"SNAPSHOT"}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.delete_snapshot(name, volume_name)

    def replicate_volume_from_snapshot(self, target_volume_name,
                                            snapshot_name, src_volume_name):
        urlreadresult =  b'{ "id": 1, "target_dataset": "pool/cinder/volume-'\
            b'ba323557","state": {"state": "FINISHED"}}'
        replicationstatresult = b'{ "id": 1, "target_dataset": "pool/cinder/'\
            b'volume-ba323557","state": {"state": "FINISHED"}}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        self.common.replication_run = MagicMock()
        self.common.replication_stats = MagicMock(return_value
                                                  = replicationstatresult)
        self.common.delete_snapshot = MagicMock()
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.replicate_volume_from_snapshot(target_volume_name,
                                                           snapshot_name,
                                                           src_volume_name)

    def promote_volume(self, volume_name):
        urlreadresult = b'null'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.promote_volume(volume_name)

    def system_version(self):
        urlreadresult = b'"TrueNAS-13.0-U8.1"'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                return self.common.system_version()

    def tunable(self):
        urlreadresult = b'[{"id":3,"value":"2","type":"LOADER","comment":"'\
            b'","enabled":true,"var":"hint.isp.0.role"},{"id":4,"value":"2'\
            b'","type":"LOADER","comment":"","enabled":true,"var":"hint.is'\
            b'p.1.role"},{"id":5,"value":"2","type":"LOADER","comment":"",'\
            b'"enabled":true,"var":"hint.isp.2.role"},{"id":6,"value":"2",'\
            b'"type":"LOADER","comment":"","enabled":true,"var":"hint.isp.'\
            b'3.role"},{"id":7,"value":"256","type":"LOADER","comment":"",'\
            b'"enabled":true,"var":"kern.cam.ctl.max_ports"}]'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                return self.common.tunable()

    def update_volume_stats(self):
        urlreadresult = b'{"id":"pool/cinder","name":"pool/cinder","pool":'\
            b'"pool","used":{"value":"4.26G","rawvalue":"4570963968","pars'\
            b'ed":4570963968,"source":"NONE"},"available":{"value":"48.9G"'\
            b',"rawvalue":"52530008064","parsed":52530008064,"source":"NON'\
            b'E"}}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.system_version = MagicMock(return_value="TrueNAS")
                return self.common.update_volume_stats()

    def extend_volume(self, name, new_size):
        urlreadresult = b'{"id":"cinder-zpool/mydataset/volume-f9ecfc53",'\
            b'"name":"cinder-zpool/mydataset/volume-f9ecfc53","pool":"poo'\
            b'l","type":"VOLUME","volsize":{"value":"2G","rawvalue":"2147'\
            b'483648","parsed":2147483648,"source":"LOCAL"},"used":{"valu'\
            b'e":"2.06G","rawvalue":"2216689664","parsed":2216689664,"sou'\
            b'rce":"NONE"},"available":{"value":"50.0G","rawvalue":"53639'\
            b'102464","parsed":53639102464,"source":"NONE"}}'
        urlrespond = MagicMock(name="urlrespond")
        urlrespondcontext = MagicMock(name="urlrespondcontext")
        urlrespond.__enter__.return_value = urlrespondcontext
        urlrespondcontext.read.return_value = urlreadresult
        with patch(request_patch):
            with patch(open_patch, return_value=urlrespond):
                self.common.extend_volume(name, new_size)

    def create_export(self, volume_name):
        return self.common.create_export(volume_name)


FakeConnector = {'initiator': 'iqn.2005-10.org.freenas.ctltarget-2b12',
                 'multipath': False,
                 'wwpns': ['10000090fa0d6754'],
                 'wwnns': ['10000090fa0d6755'],
                 'host': '10.3.1.81',
                 }


FakeSnapshot = {'name': "snap-fakeid-1111-11-11-11-11", 'volume_name': 'fake-volumeid', 'id': 'fakeid', 'volume_id': 'fake-volumeid'}


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
    'ixsystems_replication_timeout': 600
    }


class fakeiscsidriver(FreeNASISCSIDriver):

    def __init__(self, configuration):
        self.configuration = configuration
        super().__init__(configuration=configuration)
        self.common = fakecommon(configuration=configuration)
        self.common.do_custom_setup()


@ddt.ddt
class FreeNASISCSIDriverTestCase(unittest.TestCase):

    def setUp(self):
        CONF = Mock(spec=conf.Configuration)
        CONF.iscsi_helper = 'tgtadm'
        CONF.volume_dd_blocksize = 512
        CONF.volume_driver = \
            'cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver'
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
        CONF.ixsystems_replication_timeout = 600
        self.driver = fakeiscsidriver(configuration=CONF)

    def test_check_for_setup_error(self):
        self.driver.check_for_setup_error()

    @ddt.data([context.get_admin_context()])
    def test_do_setup(self, context):
        self.driver.do_setup(context)

    @ddt.data((fake_volume.fake_db_volume()))
    def test_create_volume(self, volume):
        self.driver.create_volume(volume)

    @ddt.data((fake_volume.fake_db_volume()))
    def test_delete_volume(self, volume):
        self.driver.delete_volume(volume)

    @ddt.data((context.get_admin_context(),
               fake_volume.fake_db_volume(), FakeConnector))
    @ddt.unpack
    def test_create_export(self, context, volume, connector):
        self.driver.create_export(context, volume, connector)

    @ddt.data((context.get_admin_context(), fake_volume.fake_db_volume()))
    @ddt.unpack
    def test_ensure_export(self, context, volume):
        self.driver.ensure_export(context, volume)

    @ddt.data((context.get_admin_context(), fake_volume.fake_db_volume()))
    @ddt.unpack
    def test_remove_export(self, context, volume):
        self.driver.remove_export(context, volume)

    def test_check_connection(self):
        self.driver.check_connection()

    @ddt.data((fake_volume.fake_db_volume(), FakeConnector))
    @ddt.unpack
    def test_initialize_connection(self, volume, connector):
        self.driver.initialize_connection(volume, connector)

    @ddt.data((fake_volume.fake_db_volume(), FakeConnector))
    @ddt.unpack
    def test_terminate_connection(self, volume, connector):
        self.driver.terminate_connection(volume, connector)

    @ddt.data((FakeSnapshot))
    def test_create_snapshot(self, snapshot):
        self.driver.create_snapshot(snapshot)

    @ddt.data((FakeSnapshot))
    def test_delete_snapshot(self, snapshot):
        self.driver.delete_snapshot(snapshot)

    @ddt.data((fake_volume.fake_db_volume(), FakeSnapshot))
    @ddt.unpack
    def test_create_volume_from_snapshot(self, volume, snapshot):
        self.driver.create_volume_from_snapshot(volume, snapshot)

    def test_get_volume_stats(self):
        self.driver.get_volume_stats(refresh=False)

    @ddt.data((fake_volume.fake_db_volume(), fake_volume.fake_db_volume()))
    @ddt.unpack
    def test_create_cloned_volume(self, volume, src_vref):
        self.driver.create_cloned_volume(volume, src_vref)

    @ddt.data((fake_volume.fake_db_volume(), 10))
    @ddt.unpack
    def test_extend_volume(self, volume, new_size):
        self.driver.extend_volume(volume, new_size)


if __name__ == '__main__':
    unittest.main()
