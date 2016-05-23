#vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2016 iXsystems
"""
Volume driver for iXsystems iSCSI storage systems.

This driver requires iXsystems storage systems with installed iSCSI licenses.
"""


from cinder import exception
from cinder.image import image_utils
from cinder import utils
from oslo_log import log as logging
from cinder.volume import driver
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASApiError
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer
from cinder.volume.drivers.ixsystems.options import ixsystems_basicauth_opts
from cinder.volume.drivers.ixsystems.options import ixsystems_connection_opts
from cinder.volume.drivers.ixsystems.options import ixsystems_provisioning_opts
from cinder.volume.drivers.ixsystems.options import ixsystems_transport_opts
from cinder.volume import utils as volume_utils
from cinder.i18n import _
from lxml import etree
import os
from oslo.config import cfg
import simplejson as json

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.register_opts(ixsystems_connection_opts)
CONF.register_opts(ixsystems_transport_opts)
CONF.register_opts(ixsystems_basicauth_opts)
CONF.register_opts(ixsystems_provisioning_opts)


class FreeNASISCSIDriver(driver.ISCSIDriver):
    """FREENAS iSCSI volume driver."""

    VERSION = "1.0.0"
    IGROUP_PREFIX = 'openstack-'
    
    required_flags = ['ixsystems_transport_type', 'ixsystems_login',
                      'ixsystems_password', 'ixsystems_server_hostname',
                      'ixsystems_server_port', 'ixsystems_server_iscsi_port',
                      'ixsystems_volume_backend_name', 'ixsystems_vendor_name', 'ixsystems_storage_protocol',
                      'ixsystems_datastore_pool', 'ixsystems_iqn_prefix', ]

    def __init__(self, *args, **kwargs):
        """Initialize FreeNASISCSIDriver Class."""
        super(FreeNASISCSIDriver, self).__init__(*args, **kwargs)
        self.configuration.append_config_values(ixsystems_connection_opts)
        self.configuration.append_config_values(ixsystems_basicauth_opts)
        self.configuration.append_config_values(ixsystems_transport_opts)
        self.configuration.append_config_values(ixsystems_provisioning_opts)
        self.configuration.ixsystems_iqn_prefix += ':'
        self.backend_name = self.configuration.ixsystems_volume_backend_name
        self.vendor_name = self.configuration.ixsystems_vendor_name
        self.storage_protocol = self.configuration.ixsystems_storage_protocol
        self.stats = {}

    def _generate_freenas_volume_name(self, name):
        """Create FREENAS volume / iscsitarget name from Cinder name."""
        backend_volume = 'volume-' + name.split('-')[1]
        backend_target = 'target-' + name.split('-')[1]
        backend_iqn = self.configuration.ixsystems_iqn_prefix + 'test'    #hard-coded
        return {'name': backend_volume, 'target': backend_target, 'iqn': backend_iqn}

    def _generate_freenas_volume_name_from_id(self, name):
        """Create FREENAS volume / iscsitarget name from Cinder name."""
        backend_volume = 'volume-' + name.split('-')[0]
        backend_target = 'target-' + name.split('-')[0]
        return {'name': backend_volume, 'target': backend_target}

    def _generate_freenas_snapshot_name(self, name):
        """Create FREENAS snapshot / iscsitarget name from Cinder name."""
        backend_snap = 'snap-' + name.split('-')[1]
        backend_target = 'target-' + name.split('-')[1]
        backend_iqn = self.configuration.ixsystems_iqn_prefix + 'test' #hard-coded
        return {'name': backend_snap, 'target': backend_target, 'iqn': backend_iqn}

    def _create_handle(self, **kwargs):
        """Instantiate handle (client) for API communication with
            iXsystems FREENAS server
        """
        host_system = kwargs['hostname']
        LOG.debug('Using iXsystems FREENAS server: %s', host_system)
        self.handle = FreeNASServer(host=host_system,
                                 port=kwargs['port'],
                                 username=kwargs['login'],
                                 password=kwargs['password'],
                                 api_version=kwargs['api_version'],
                                 transport_type=kwargs['transport_type'],
                                 style=FreeNASServer.STYLE_LOGIN_PASSWORD)

    def _check_flags(self):
        """Check if any required iXsystems FREENAS configuration flag is missing."""
        for flag in self.required_flags:
            if not getattr(self.configuration, flag, None):
                print "missing flag :", flag
                raise exception.CinderException(_('%s is not set') % flag)

    def check_for_setup_error(self):
        """Check for iXsystems FREENAS configuration parameters."""
        self._check_flags()

    def _do_custom_setup(self):
        """Setup iXsystems FREENAS driver."""
        self._create_handle(hostname=self.configuration.ixsystems_server_hostname,
                            port=self.configuration.ixsystems_server_port,
                            login=self.configuration.ixsystems_login,
                            password=self.configuration.ixsystems_password,
                            api_version=self.configuration.ixsystems_api_version,
                            transport_type=
                            self.configuration.ixsystems_transport_type)
        if not self.handle:
                raise FreeNASApiError("Failed to create handle for FREENAS server")

    def do_setup(self, context):
        """Setup iXsystems FREENAS driver
            Check for configuration flags and setup iXsystems FREENAS client
        """
        self.check_for_setup_error()
        self._do_custom_setup()

    def _get_iscsi_portal(self):
        """Get iscsi portal info from iXsystems FREENAS configuration."""
        return "%s:%s" % (self.configuration.ixsystems_server_hostname,
                          self.configuration.ixsystems_server_iscsi_port)

    def _create_volume(self, name, size):
        """Creates a volume of specified size
        """
        params = {}
        params['name'] = name
        params['volsize'] = str(size) + 'G'
        jparams = json.dumps(params)
        request_urn = ('%s/%s/%s/') % (FreeNASServer.VOLUME_TABLE, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS)
        LOG.debug('_create_volume params : %s', params)
        LOG.debug('_create_volume urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jparams)
        LOG.debug('_create_volume response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _target_to_extent(self, extent_id):
        """crates a relationship between iscsi target to iscsi extent"""   
        
        LOG.debug('_target_to_extent extend id : %s', extent_id)
        
        request_urn = ('%s/') % (FreeNASServer.ISCSI_EXTENT_TABLE)
        params = {}
        params['iscsi_target'] = FreeNASServer.TARGET_ID
        params['iscsi_extent'] = extent_id

        jparams = json.dumps(params)
        LOG.debug('_create_iscsitarget params : %s', jparams)

        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND, request_urn, jparams)

        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating relation between target and extent: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        
    def _create_iscsitarget(self, name, volume_name, volume_size,
                            from_snapshot=False):
        """Creates a iSCSI target on specified volume OR snapshot
        """
        
        params = {}
        if from_snapshot:
            params['Source'] = volume_name
        else:
            params['iscsi_target_extent_type'] = 'Disk'
            params['iscsi_target_extent_name'] = name
        mnt_point = ('zvol/%s/%s') % (self.configuration.ixsystems_datastore_pool, volume_name)
        params['iscsi_target_extent_disk'] = mnt_point
        jparams = json.dumps(params)

        LOG.debug('_create_iscsitarget params : %s', jparams)

        request_urn = ('%s/') % (FreeNASServer.ISCSI_TARGET_TABLE)

        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jparams)

        LOG.debug('_create_iscsitarget response : %s', json.dumps(ret))

        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        self._target_to_extent(json.loads(ret['response'])['id'])

    def create_volume(self, volume):
        """Creates a volume of specified size and export it as iscsi target."""
        LOG.debug('create_volume : volume name :: %s', volume['name'])

        freenas_volume = self._generate_freenas_volume_name(volume['name'])
        
        LOG.debug('volume name after freenas generate : %s', json.dumps(freenas_volume))

        freenas_volume['size'] = volume['size']
        freenas_volume['target_size'] = volume['size']

        self._create_volume(freenas_volume['name'], freenas_volume['size'])
        self._create_iscsitarget(freenas_volume['target'], freenas_volume['name'],
                                 freenas_volume['target_size'])

    def _get_iscsitarget_id(self, name):
        """get iscsi target id using iscsi target name as for 
        deleting iscsi target name is not used but id is
        """
        request_urn = ('%s/') % (FreeNASServer.ISCSI_TARGET_TABLE)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND, request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        
        resp = json.loads(ret['response'])

        try:
            return (item for item in resp if item["iscsi_target_extent_name"] == name).next()['id']
        except StopIteration:
            return 0

    def _delete_iscsitarget(self, name):
        """Deletes specified iSCSI target
        """
        target_id = self._get_iscsitarget_id(name)

        #if target_id exists i.e. extend exists
        if target_id:
            request_urn = ('%s/%s/') % (FreeNASServer.ISCSI_TARGET_TABLE, target_id)
            LOG.debug('_delete_iscsitarget urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting iscsi target: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)

            request_urn = ('%s/%s/') % (FreeNASServer.ISCSI_EXTENT_TABLE, target_id)
            LOG.debug('_delete_iscsi_target_extent_relationship urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)

    def _delete_volume(self, name):
        """Deletes specified volume
        """
        request_urn = ('%s/%s/%s/%s/') % (FreeNASServer.VOLUME_TABLE, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS, name)
        LOG.debug('_delete_volume urn : %s', request_urn)

        ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)


    def delete_volume(self, volume):
        """Deletes volume and corresponding iscsi target."""
        LOG.debug('delete_volume %s', volume['name'])

        freenas_volume = self._generate_freenas_volume_name(volume['name'])

        if freenas_volume['target']:
            self._delete_iscsitarget(freenas_volume['target'])
        if freenas_volume['name']:
            self._delete_volume(freenas_volume['name'])

    def list_volumes(self):
        """Fetches available list of iscsi targets
        """
        LOG.debug('list_volumes')
        try:
            request_urn = ('%s/') % (FreeNASServer.ISCSI_TARGET_TABLE)
            ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                             request_urn,
                                             None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = _("Error while listing iscsi targets")
                LOG.error(msg % msg)
            else:
                return ret['response']

        except FreeNASApiError as error:
            msg = _("Error while listing volumes ")
            LOG.error(msg % msg)

    def create_export(self, context, volume):
        """Driver entry point to get the export info for a new volume."""
        LOG.debug('create_export %s', volume['name'])

        freenas_volume = self._generate_freenas_volume_name(volume['name'])

        if freenas_volume is None:
            LOG.error(_('Error in exporting FREENAS volume!'))
            handle = None
        else:
            handle = "%s:%s,%s %s" % \
                     (self.configuration.ixsystems_server_hostname,
                      self.configuration.ixsystems_server_iscsi_port,
                      1,
                      freenas_volume['iqn'])

        LOG.debug('provider_location: %s', handle)
        return {'provider_location': handle}

    def ensure_export(self, context, volume):
        """Driver entry point to get the export info for an existing volume."""
        LOG.debug('ensure_export %s', volume['name'])

        freenas_volume = self._generate_freenas_volume_name(volume['name'])
        if freenas_volume is None:
            LOG.error(_('Error in exporting FREENAS volume!'))
            handle = None
        else:
            handle = "%s:%s,%s %s" % \
                     (self.configuration.ixsystems_server_hostname,
                      self.configuration.ixsystems_server_iscsi_port,
                      1,
                      freenas_volume['iqn'])

        LOG.debug('provider_location: %s', handle)
        return {'provider_location': handle}

    def remove_export(self, context, volume):
        """Driver exntry point to remove an export for a volume.
            we have nothing to do for unexporting.
        """
        pass

    def initialize_connection(self, volume, connector):
        """Driver entry point to attach a volume to an instance."""
        freenas_volume = self._generate_freenas_volume_name(volume['name'])
        if not freenas_volume['name']:
            # is this snapshot?
            freenas_volume = self._generate_freenas_snapshot_name(volume['name'])

        properties = {}
        properties['target_discovered'] = False
        properties['target_portal'] = self._get_iscsi_portal()
        properties['target_iqn'] = freenas_volume['iqn']
        properties['volume_id'] = volume['id']
        
        LOG.debug('initialize_connection data: %s', properties)
        return {'driver_volume_type': 'iscsi', 'data': properties}

    def terminate_connection(self, volume, connector, **kwargs):
        """Driver entry point to detach a volume from an instance."""
        pass

    def _create_snapshot(self, name, volume_name):
        """Creates a snapshot of specified volume."""
        args = {}
        args['dataset'] = ('%s/%s')  % (self.configuration.ixsystems_datastore_pool, volume_name)
        args['name'] =  name
        jargs = json.dumps(args)
        request_urn = ('%s/') % (FreeNASServer.SNAPSHOT_TABLE)
        
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while creating snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def _delete_snapshot(self, name, volume_name):
        """Delets a snapshot of specified volume."""
        request_urn = ('%s/%s/%s@%s/') % (FreeNASServer.SNAPSHOT_TABLE, self.configuration.ixsystems_datastore_pool, volume_name, name)
        try:
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def create_snapshot(self, snapshot):
        """Driver entry point for creating a snapshot."""
        LOG.debug('create_snapshot %s', snapshot['name'])
        
        freenas_snapshot = self._generate_freenas_snapshot_name(snapshot['name'])
        freenas_volume = self._generate_freenas_volume_name(snapshot['volume_name'])

        self._create_snapshot(freenas_snapshot['name'], freenas_volume['name'])

    def delete_snapshot(self, snapshot):
        """Driver entry point for deleting a snapshot."""
        LOG.debug('delete_snapshot %s', snapshot['name'])
        LOG.debug('delete_snapshot volume id %s', snapshot['volume_name'])
        freenas_snapshot = self._generate_freenas_snapshot_name(snapshot['name'])
        freenas_volume = self._generate_freenas_volume_name(snapshot['volume_name'])
        
        self._delete_snapshot(freenas_snapshot['name'], freenas_volume['name'])
    
    def _copy_volume(self, destination, source, size):
        """Makes a full copy from source volume."""
        context = None
        properties = utils.brick_get_connector_properties()
        dest_attach = self._attach_volume(context, destination, properties)
        src_attach = self._attach_volume(context, source, properties)
        block_size = self.configuration.volume_dd_blocksize

        dest_device = dest_attach['device']['path']
        src_device = src_attach['device']['path']
        try:
            volume_utils.copy_volume(src_device, dest_device, size * 1024,
                                     block_size, True, self._execute)

        finally:
            self._detach_volume(dest_attach)
            self._detach_volume(src_attach)
            self.terminate_connection(destination, properties)
            self.terminate_connection(source, properties)
    
    def _get_size_in_gb(self, size_in_bytes):
        "convert size in gbs"
        return size_in_bytes/(1024*1024*1024)

    def _create_volume_from_snapshot(self, name, snapshot_name, snap_zvol_name):
        "creates a volume from snapshot"
        LOG.debug('create_volume_from_snapshot')
        
        args = {}
        args['name'] = ('%s/%s')  % (self.configuration.ixsystems_datastore_pool, name)
        jargs = json.dumps(args)
        
        request_urn = ('%s/%s/%s@%s/%s/') % (FreeNASServer.SNAPSHOT_TABLE, self.configuration.ixsystems_datastore_pool, snap_zvol_name, snapshot_name, FreeNASServer.CLONE)
        
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while creating snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)


    def create_volume_from_snapshot(self, volume, snapshot):
        """Creates a volume from snapshot."""
        LOG.debug('create_volume_from_snapshot %s', snapshot['name'])

        existing_vol = self._generate_freenas_volume_name(snapshot['volume_name'])
        freenas_snapshot = self._generate_freenas_snapshot_name(snapshot['name'])
        freenas_volume = self._generate_freenas_volume_name(volume['name'])
        freenas_volume['size'] = volume['size']
        freenas_volume['target_size'] = volume['size']

        self._create_volume_from_snapshot(freenas_volume['name'], freenas_snapshot['name'], existing_vol['name'])
        self._create_iscsitarget(freenas_volume['target'], freenas_volume['name'],
                                 freenas_volume['target_size'])


    def _update_volume_stats(self):
        """Retrieve stats info from volume group
            REST API: $ GET /pools/mypool "size":95,"allocated":85,
        """
        LOG.debug('_update_volume_stats')

        request_urn = ('%s/%s/') % (FreeNASServer.VOLUME_TABLE, self.configuration.ixsystems_datastore_pool)
        
        LOG.debug('request_urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug("_update_volume Response : %s", json.dumps(ret))
        
        data = {}
        data["volume_backend_name"] = self.backend_name
        data["vendor_name"] =  self.vendor_name
        data["driver_version"] = self.VERSION
        data["storage_protocol"] = self.storage_protocol
        data['total_capacity_gb'] = self._get_size_in_gb(json.loads(ret['response'])['avail'] + json.loads(ret['response'])['used'])
        data['free_capacity_gb'] = self._get_size_in_gb(json.loads(ret['response'])['avail'])
        data['reserved_percentage'] = \
            self.configuration.ixsystems_reserved_percentage
        data['reserved_percentage'] = 0
        data['QoS_support'] = False

        self.stats = data

    def get_volume_stats(self, refresh=False):
        """Get stats info from volume group / pool."""
        if refresh:
            self._update_volume_stats()
        LOG.debug('get_volume_stats: %s', self.stats)
        return self.stats

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        """Fetch the image from image_service and write it to the volume."""
        LOG.debug('copy_image_to_volume %s', volume['name'])

        properties = utils.brick_get_connector_properties()
        attach_info = self._attach_volume(context, volume, properties)
        block_size = self.configuration.volume_dd_blocksize

        try:
            image_utils.fetch_to_raw(context,
                                     image_service,
                                     image_id,
                                     attach_info['device']['path'],
                                     block_size)
        finally:
            self._detach_volume(attach_info)
            self.terminate_connection(volume, properties)

    def copy_volume_to_image(self, context, volume, image_service, image_meta):
        """Copy the volume to the specified image."""
        LOG.debug('copy_volume_to_image %s.', volume['name'])

        properties = utils.brick_get_connector_properties()
        attach_info = self._attach_volume(context, volume, properties)

        try:
            image_utils.upload_volume(context,
                                      image_service,
                                      image_meta,
                                      attach_info['device']['path'])
        finally:
            self._detach_volume(attach_info)
            self.terminate_connection(volume, properties)

    def _attach_volume(self, context, volume, properties):
        """Connect the volume to the host."""
        LOG.debug('_attach_volume %s', volume['name'])
        connection = self.initialize_connection(volume, properties)

        # Use Brick's code to do attach/detach
        #use_multipath = self.configuration.use_multipath_for_image_xfer
        use_multipath = False
        device_scan_attempts = self.configuration.num_volume_device_scan_tries
        protocol = connection['driver_volume_type']

        connector = utils.brick_get_connector(protocol,
                                              use_multipath=use_multipath,
                                              device_scan_attempts=
                                              device_scan_attempts)

        device = connector.connect_volume(connection['data'])
        host_device = device['path']

        if not connector.check_valid_device(host_device):
            reason = "Unable to access the backend storage via path %s" % \
                     host_device
            raise exception.DeviceUnavailable(reason, path=host_device)

        return {'conn': connection, 'device': device, 'connector': connector}

    def _detach_volume(self, attach_info):
        """Disconnect the volume from the host."""
        LOG.debug('_detach_volume %s', attach_info['device'])

        # Use Brick's code to do attach/detach
        connector = attach_info['connector']
        connector.disconnect_volume(attach_info['conn']['data'],
                                    attach_info['device'])

    def _create_cloned_volume_to_snapshot_map(self, volume_name, snapshot):
        """ maintain a mapping between cloned volume and tempary snapshot"""
        map_file = os.path.join(CONF.volumes_dir, volume_name)
        jparams = json.dumps(snapshot)
        try:
             fd = open(map_file, 'w+')
             fd.write(jparams)
             fd.close()
        except Exception as e:
             LOG.error(_('_create_halo_volume_name_map: %s') % e)

    def create_cloned_volume(self, volume, src_vref):
        """Creates a volume from source volume."""
        LOG.debug('create_cloned_volume: %s', src_vref['id'])

        context = None
        temp_snapshot = {'volume_name': src_vref['name'],
                         'name': 'name-c%s' % src_vref['id']}
        
        self.create_snapshot(temp_snapshot)
        self.create_volume_from_snapshot(volume, temp_snapshot)
        self._create_cloned_volume_to_snapshot_map(volume['name'], temp_snapshot)
        self.delete_snapshot(temp_snapshot)
        return self.create_export(context, volume)

    def _extend_volume(self, name, new_size):
        """Extend an existing volumes size."""
        LOG.debug('_extend__volume name: %s', name)
        
        params = {}
        params['volsize'] = str(new_size) + 'G'
        jparams = json.dumps(params)
        request_urn = ('%s/%s/%s/%s/') % (FreeNASServer.VOLUME_TABLE, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS, name)
        ret = self.handle.invoke_command(FreeNASServer.UPDATE_COMMAND,
                                         request_urn, jparams)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while extending volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
    
    def extend_volume(self, volume, new_size):
        """Driver entry point to extend an existing volumes size."""
        LOG.debug('extend_volume %s', volume['name'])
        
        freenas_volume = self._generate_freenas_volume_name(volume['name'])
        freenas_new_size = new_size
        
        if volume['size'] != freenas_new_size:
            self._extend_volume(freenas_volume['name'], freenas_new_size)

