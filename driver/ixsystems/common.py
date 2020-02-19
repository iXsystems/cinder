#vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2016 iXsystems
from oslo_log import log as logging
from cinder import exception
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASApiError
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer
from oslo_config import cfg
import os
from cinder.volume.drivers.ixsystems import utils as ix_utils
import simplejson as json

LOG = logging.getLogger(__name__)


class TrueNASCommon(object):

    VERSION = "1.0.0"
    IGROUP_PREFIX = 'openstack-'

    required_flags = ['ixsystems_transport_type', 'ixsystems_login',
                      'ixsystems_password', 'ixsystems_server_hostname',
                      'ixsystems_server_port', 'ixsystems_server_iscsi_port',
                      'ixsystems_volume_backend_name', 'ixsystems_vendor_name', 'ixsystems_storage_protocol',
                      'ixsystems_datastore_pool', 'ixsystems_iqn_prefix', ]

    def __init__(self, configuration=None):

        self.configuration = configuration        
        self.backend_name = self.configuration.ixsystems_volume_backend_name
        self.vendor_name = self.configuration.ixsystems_vendor_name
        self.storage_protocol = self.configuration.ixsystems_storage_protocol
        self.stats = {}

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
        if not self.handle:
            raise FreeNASApiError("Failed to create handle for FREENAS server")    

    def _check_flags(self):
        """Check if any required iXsystems FREENAS configuration flag is missing."""
        for flag in self.required_flags:
            if not getattr(self.configuration, flag, None):
                print("missing flag :", flag)
                raise exception.CinderException(_('%s is not set') % flag)

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

    def _create_volume(self, name, size):
        """Creates a volume of specified size
        """
        params = {}
        params['name'] = name
        params['volsize'] = str(size) + 'G'
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        request_urn = ('%s/%s/%s/') % (FreeNASServer.REST_API_VOLUME, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS)
        LOG.debug('_create_volume params : %s', params)
        LOG.debug('_create_volume urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jparams)
        LOG.debug('_create_volume response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)




    def _target_to_extent(self, target_id, extent_id):
        """Create  relationship between iscsi target to iscsi extent"""

        LOG.debug('_target_to_extent target id : %s extend id : %s', target_id, extent_id)

        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET_TO_EXTENT)
        params = {}
        params['iscsi_target'] = target_id
        params['iscsi_extent'] = extent_id
        params['iscsi_lunid'] = 0   # https://www.ixsystems.com/community/threads/will-it-openstack.64073/page-2#post-514090
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')

        LOG.debug('_create_target_to_extent params : %s', json.dumps(params))

        tgt_ext = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND, request_urn, jparams)

        if tgt_ext['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating relation between target and extent: %s' % tgt_ext['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_target_group(self, target_id):

        tgt_grp_params = {}
        tgt_grp_params["iscsi_target"] = target_id
        tgt_grp_params["iscsi_target_portalgroup"] = self.configuration.ixsystems_portal_id  #TODO: Decide to create portal or not
        tgt_grp_params["iscsi_target_initiatorgroup"] = self.configuration.ixsystems_initiator_id #TODO: Decide to create initiator or not
        jtgt_grp_params = json.dumps(tgt_grp_params)
        jtgt_grp_params = jtgt_grp_params.encode('utf8')
        tgt_request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET_GROUP)
        tgtgrp = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         tgt_request_urn, jtgt_grp_params)

        LOG.debug('_create_target_group response : %s', json.dumps(tgtgrp))

        if tgtgrp['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target: %s' % tgtgrp['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_target(self, name):

        tgt_params = {}
        tgt_params["iscsi_target_name"] = name
        jtgt_params = json.dumps(tgt_params)
        jtgt_params = jtgt_params.encode('utf8')
        LOG.debug('_create_target params : %s', json.dumps(tgt_params))
        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET)
        target = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jtgt_params)
        LOG.debug('_create_target response : %s', json.dumps(target))

        if target['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target: %s' % target['response'])
            raise FreeNASApiError('Unexpected error', msg)

        target_id = json.loads(target['response'])['id']
        self._create_target_group(target_id)

        return target_id

    def _create_extent(self, name, volume_name,from_snapshot=False):

        ext_params = {}
        if from_snapshot:
            ext_params['Source'] = volume_name
        else:
            ext_params['iscsi_target_extent_type'] = 'Disk'
            ext_params['iscsi_target_extent_name'] = name
        mnt_point = ('zvol/%s/%s') % (self.configuration.ixsystems_datastore_pool, volume_name)
        ext_params['iscsi_target_extent_disk'] = mnt_point
        jext_params = json.dumps(ext_params)
        jext_params = jext_params.encode('utf8')
        request_urn = ('%s/') % (FreeNASServer.REST_API_EXTENT)
        extent = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jext_params)

        LOG.debug('_create_iscsitarget extent response : %s', json.dumps(extent))

        if extent['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target extent: %s' % extent['response'])
            raise FreeNASApiError('Unexpected error', msg)

        return json.loads(extent['response'])['id']

    def get_iscsitarget_id(self, name):
        """get iscsi target id from target name
        """
        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND, request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        
        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp if item["iscsi_target_name"] == name).__next__()['id']
        except StopIteration:
            return 0

    def get_tgt_ext_id(self, name):
        """Get target-extent mapping id from target name.
        """
        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET_TO_EXTENT)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND, request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        
        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp if item["iscsi_target"] == name).__next__()['id']
        except StopIteration:
            return 0

    def get_extent_id(self, name):
        """Get Extent ID from Extent Name
        """
        request_urn = ('%s/') % (FreeNASServer.REST_API_EXTENT)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND, request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp if item["iscsi_target_extent_name"] == name).__next__()['id']
        except StopIteration:
            return 0

    def _create_iscsitarget(self, name, volume_name):
        """Creates a iSCSI target on specified volume OR snapshot
        TODO : Skipped part for snapshot, review once iscsi target working
        TODO: Add cleanup if any operation fails
        """

        #Create iscsi target for specified volume
        tgt_id = self._create_target(name)

        #Create extent for iscsi target for specified volume
        ext_id = self._create_extent(name, volume_name)
     
        #Create target to extent mapping for specified volume
        self._target_to_extent(tgt_id, ext_id)

    def delete_target_to_extent(self, tgt_ext_id):
        pass
    
    def delete_target(self, target_id):
        if target_id:
            request_urn = ('%s/%s/') % (FreeNASServer.REST_API_TARGET, target_id)
            LOG.debug('_delete_iscsitarget urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting iscsi target: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)

    def delete_extent(self, extent_id):

        if extent_id:
            request_urn = ('%s/%s/') % (FreeNASServer.REST_API_EXTENT, extent_id)
            LOG.debug('delete_extent urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
            
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting iscsi extent: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)

    def _delete_iscsitarget(self, name):
        """Deletes specified iSCSI target
        """
        tgt_ext_id = self.get_tgt_ext_id(name)
        target_id = self.get_iscsitarget_id(name)
        extent_id = self.get_extent_id(name)
        
        self.delete_target_to_extent(tgt_ext_id)
        self.delete_target(target_id)
        self.delete_extent(extent_id)



    def _delete_volume(self, name):
        """Deletes specified volume
        """
        request_urn = ('%s/%s/%s/%s/') % (FreeNASServer.REST_API_VOLUME, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS, name)
        LOG.debug('_delete_volume urn : %s', request_urn)

        ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_snapshot(self, name, volume_name):
        """Creates a snapshot of specified volume."""
        args = {}
        args['dataset'] = ('%s/%s')  % (self.configuration.ixsystems_datastore_pool, volume_name)
        args['name'] =  name
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")
        request_urn = ('%s/') % (FreeNASServer.REST_API_SNAPSHOT)
        LOG.debug('_create_snapshot urn : %s', request_urn)

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
        request_urn = ('%s/%s/%s@%s/') % (FreeNASServer.REST_API_SNAPSHOT, self.configuration.ixsystems_datastore_pool, volume_name, name)
        try:
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def _create_volume_from_snapshot(self, name, snapshot_name, snap_zvol_name):
        "creates a volume from snapshot"
        LOG.debug('create_volume_from_snapshot')

        args = {}
        args['name'] = ('%s/%s')  % (self.configuration.ixsystems_datastore_pool, name)
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")

        request_urn = ('%s/%s/%s@%s/%s/') % (FreeNASServer.REST_API_SNAPSHOT, self.configuration.ixsystems_datastore_pool, snap_zvol_name, snapshot_name, FreeNASServer.CLONE)

        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while creating snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)


    def _update_volume_stats(self):
        """Retrieve stats info from volume group
            REST API: $ GET /pools/mypool "size":95,"allocated":85,
        """
        LOG.debug('_update_volume_stats')

        request_urn = ('%s/%s/') % (FreeNASServer.REST_API_VOLUME, self.configuration.ixsystems_datastore_pool)

        LOG.debug('request_urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug("_update_volume Response : %s", json.dumps(ret))

        data = {}
        data["volume_backend_name"] = self.backend_name
        data["vendor_name"] =  self.vendor_name
        data["driver_version"] = self.VERSION
        data["storage_protocol"] = self.storage_protocol
        data['total_capacity_gb'] = ix_utils.get_size_in_gb(json.loads(ret['response'])['avail'] + json.loads(ret['response'])['used'])
        data['free_capacity_gb'] = ix_utils.get_size_in_gb(json.loads(ret['response'])['avail'])
        data['reserved_percentage'] = \
            self.configuration.ixsystems_reserved_percentage
        data['reserved_percentage'] = 0
        data['QoS_support'] = False

        self.stats = data
        return self.stats

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

    def _extend_volume(self, name, new_size):
        """Extend an existing volumes size."""
        LOG.debug('_extend__volume name: %s', name)

        params = {}
        params['volsize'] = str(new_size) + 'G'
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        request_urn = ('%s/%s/%s/%s/') % (FreeNASServer.REST_API_VOLUME, self.configuration.ixsystems_datastore_pool, FreeNASServer.ZVOLS, name)
        ret = self.handle.invoke_command(FreeNASServer.UPDATE_COMMAND,
                                         request_urn, jparams)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while extending volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)


    def _create_export(self, volume_name):
        freenas_volume = ix_utils.generate_freenas_volume_name(volume_name, self.configuration.ixsystems_iqn_prefix)
        if freenas_volume is None:
            LOG.error(_('Error in exporting FREENAS volume!'))
            handle = None
        else:
            handle = "%s:%s,%s %s" % \
                     (self.configuration.ixsystems_server_hostname,
                      self.configuration.ixsystems_server_iscsi_port,
                      freenas_volume['target'],
                      freenas_volume['iqn'])

        LOG.debug('provider_location: %s', handle)
        return handle
