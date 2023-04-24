# Copyright (c) 2016 iXsystems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import simplejson as json
import urllib.parse

from cinder import exception
from cinder.i18n import _
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASApiError
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer
from cinder.volume.drivers.ixsystems import utils as ix_utils
from oslo_config import cfg
from oslo_log import log as logging
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class TrueNASCommon(object):

    VERSION = "2.0.0"
    IGROUP_PREFIX = 'openstack-'

    required_flags = ['ixsystems_transport_type', 'ixsystems_server_hostname',
                      'ixsystems_server_port', 'ixsystems_server_iscsi_port',
                      'ixsystems_volume_backend_name', 'ixsystems_vendor_name',
                      'ixsystems_storage_protocol', 'ixsystems_datastore_pool',
                      'ixsystems_dataset_path', 'ixsystems_iqn_prefix',]

    def __init__(self, configuration=None):
        self.configuration = configuration
        self.backend_name = self.configuration.ixsystems_volume_backend_name
        self.vendor_name = self.configuration.ixsystems_vendor_name
        self.storage_protocol = self.configuration.ixsystems_storage_protocol
        self.apikey = self.configuration.ixsystems_apikey
        self.stats = {}

    def _create_handle(self, **kwargs):
        """Instantiate client for API comms with iXsystems FREENAS server."""

        host_system = kwargs['hostname']
        LOG.debug('Using iXsystems FREENAS server: %s', host_system)
        self.handle = FreeNASServer(
            host=host_system,
            port=kwargs['port'],
            username=kwargs['login'],
            password=kwargs['password'],
            apikey=kwargs['apikey'],
            api_version=kwargs['api_version'],
            transport_type=kwargs['transport_type'])
        if not self.handle:
            raise FreeNASApiError("Failed to create handle for FREENAS server")

    def _check_flags(self):
        """Check if any required iXsystems configuration flag is missing."""
        for flag in self.required_flags:
            if not getattr(self.configuration, flag, None):
                raise exception.CinderException(_('%s is not set') % flag)

    def _do_custom_setup(self):
        """Setup iXsystems FREENAS driver."""
        self._create_handle(
            hostname=self.configuration.ixsystems_server_hostname,
            port=self.configuration.ixsystems_server_port,
            login=self.configuration.ixsystems_login,
            password=self.configuration.ixsystems_password,
            apikey=self.configuration.ixsystems_apikey,
            api_version=self.configuration.ixsystems_api_version,
            transport_type=self.configuration.ixsystems_transport_type)

        if not self.handle:
            raise FreeNASApiError(
                "Failed to create handle for FREENAS server")

    def _create_volume(self, name, size):
        """Creates a volume of specified size."""

        params = {}
        params['name'] = self.configuration.ixsystems_dataset_path + '/' + name
        params['type'] = 'VOLUME'
        params['volsize'] = ix_utils.get_bytes_from_gb(size)
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        request_urn = ('%s') % (FreeNASServer.REST_API_VOLUME)
        LOG.debug('_create_volume params : %s', params)
        LOG.debug('_create_volume urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jparams)
        LOG.debug('_create_volume response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _target_to_extent(self, target_id, extent_id):
        """Create relationship between iscsi target to iscsi extent."""

        LOG.debug('_target_to_extent target id : %s extend id : %s',
                  target_id, extent_id)

        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET_TO_EXTENT)
        params = {}
        params['target'] = target_id
        params['extent'] = extent_id
        # params['iscsi_lunid'] = 0   # no longer needed with API v2.0
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')

        LOG.debug('_create_target_to_extent params : %s', json.dumps(params))

        tgt_ext = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jparams)

        LOG.debug('_target_to_extent response : %s', json.dumps(tgt_ext))

        if tgt_ext['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating relation between '
                   'target and extent: %s' % tgt_ext['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_target(self, name):
        # v2.0 API - targetgroup can now be added when target is created
        targetgroup_params = [{}]
        # TODO: Decide to create portal or not
        targetgroup_params[0]['portal'] = int(
            self.configuration.ixsystems_portal_id)

        # TODO: Decide to create initiator or not
        targetgroup_params[0]['initiator'] = int(
            self.configuration.ixsystems_initiator_id)
        tgt_params = {}
        tgt_params['name'] = name
        tgt_params['groups'] = targetgroup_params
        jtgt_params = json.dumps(tgt_params)
        jtgt_params = jtgt_params.encode('utf8')
        LOG.debug('_create_target params : %s', json.dumps(tgt_params))
        request_urn = ('%s/') % (FreeNASServer.REST_API_TARGET)
        target = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                            request_urn, jtgt_params)
        LOG.debug('_create_target response : %s', json.dumps(target))

        if target['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target: {}'.format(
                target['response']))
            raise FreeNASApiError('Unexpected error', msg)

        target_id = json.loads(target['response'])['id']
        # self._create_target_group(target_id)

        return target_id

    def _create_extent(self, name, volume_name, from_snapshot=False):
        ext_params = {}
        if from_snapshot:
            ext_params['Source'] = volume_name
        else:
            ext_params['type'] = 'DISK'
            ext_params['name'] = name
        ext_params['disk'] = ('zvol/%s/%s') % (
            self.configuration.ixsystems_dataset_path, volume_name)
        jext_params = json.dumps(ext_params)
        LOG.debug('_create_extent params : %s', jext_params)
        jext_params = jext_params.encode('utf8')
        request_urn = ('%s/') % (FreeNASServer.REST_API_EXTENT)
        extent = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                            request_urn, jext_params)

        LOG.debug('_create_extent response : %s', json.dumps(extent))

        if extent['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while creating iscsi target extent: {}'.format(
                extent['response']))
            raise FreeNASApiError('Unexpected error', msg)

        return json.loads(extent['response'])['id']

    def get_iscsitarget_id(self, name):
        """get iscsi target id from target name."""

        request_urn = ('%s') % (FreeNASServer.REST_API_TARGET)
        LOG.debug('get_iscsitarget_id request_urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug('get_iscsitarget_id response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp
                    if item['name'] == name).__next__()['id']
        except StopIteration:
            return 0

    def get_tgt_ext_id(self, name):
        """Get target-extent mapping id from target name."""

        request_urn = ('%s') % (FreeNASServer.REST_API_TARGET_TO_EXTENT)
        LOG.debug('get_tgt_ext_id urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug('get_tgt_ext_id response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting iscsi target: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp
                    if item['target'] == name).__next__()['id']
        except StopIteration:
            return 0

    def get_extent_id(self, name):
        """Get Extent ID from Extent Name."""

        request_urn = ('%s') % (FreeNASServer.REST_API_EXTENT)
        LOG.debug('get_extent_id urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug('get_extent_id response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while getting extent id: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return (item for item in resp
                    if item['name'] == name).__next__()['id']
        except StopIteration:
            return 0

    def _create_iscsitarget(self, name, volume_name):
        """Creates a iSCSI target on specified volume OR snapshot.

           TODO : Skipped part for snapshot, review once iscsi target working
           TODO: Add cleanup if any operation fails
        """

        # Create iscsi target for specified volume
        tgt_id = self._create_target(name)

        # Create extent for iscsi target for specified volume
        ext_id = self._create_extent(name, volume_name)

        # Create target to extent mapping for specified volume
        self._target_to_extent(tgt_id, ext_id)

    def delete_target_to_extent(self, tgt_ext_id):
        pass

    def delete_target(self, target_id):
        if target_id:
            request_urn = ('%s/id/%s') % (
                FreeNASServer.REST_API_TARGET, target_id)
            LOG.debug('delete_target urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug('delete_target response : %s', json.dumps(ret))
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = (
                    'Error while deleting iscsi target: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)

    def delete_extent(self, extent_id):
        if extent_id:
            request_urn = ('%s/id/%s') % (
                FreeNASServer.REST_API_EXTENT, extent_id)
            LOG.debug('delete_extent urn : %s', request_urn)
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug('delete_extent response : %s', json.dumps(ret))
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = (
                    'Error while deleting iscsi extent: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)

    def _delete_iscsitarget(self, name):
        """Deletes specified iSCSI target."""
        tgt_ext_id = self.get_tgt_ext_id(name)
        target_id = self.get_iscsitarget_id(name)
        extent_id = self.get_extent_id(name)

        self.delete_target_to_extent(tgt_ext_id)
        self.delete_target(target_id)
        self.delete_extent(extent_id)

    def _dependent_clone(self, name):
        """returns the fullname of snapshot used to create volume 'name'."""
        request_urn = ('%s/id/%s%s') % (
            FreeNASServer.REST_API_VOLUME,
            urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/'),
            name)
        LOG.debug('_dependent_clones urn : %s', request_urn)
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug('_dependent_clones response : %s', json.dumps(ret))
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while getting volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)
        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        return resp['origin']['value']

    def _delete_volume(self, name):
        """Deletes specified volume."""
        request_urn = ('%s/id/%s%s') % (
            FreeNASServer.REST_API_VOLUME,
            urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/'),
            name)
        LOG.debug('_delete_volume urn : %s', request_urn)
        # add check for dependent clone, if exists will delete
        clone = self._dependent_clone(name)
        ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
        LOG.debug('_delete_volume response : %s', json.dumps(ret))

        # delete the cloned-from snapshot.
        # Must check before deleting volume, but delete snapshot after
        if clone:
            fullvolume, snapname = clone.split('@')
            temp, snapvol = fullvolume.rsplit('/', 1)
            self._delete_snapshot(snapname, snapvol)

        # When deleting volume with dependent snapsnot clone, 422 error triggered. Throw VolumeIsBusy exception ensures
        # upper stream cinder manager mark volume status available instead of error-deleting.
        if ret['status'] == 'error' and ret['code'] == 422:
            errorexception = exception.VolumeIsBusy(
                _("Cannot delete volume when clone child volume or snapshot exists!"), volume_name=name)
            raise errorexception
        elif ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while deleting volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_snapshot(self, name, volume_name):
        """Creates a snapshot of specified volume."""
        args = {}
        args['dataset'] = ('%s/%s') % (
            self.configuration.ixsystems_dataset_path, volume_name)
        args['name'] = name
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")
        request_urn = ('%s') % (FreeNASServer.REST_API_SNAPSHOT)
        LOG.debug('_create_snapshot urn : %s', request_urn)

        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            LOG.debug('_create_snapshot response : %s', json.dumps(ret))
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while creating snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def _delete_snapshot(self, name, volume_name):
        """Delets a snapshot of specified volume."""
        LOG.debug('_delete_snapshot, deleting name: %s from volume: %s',
                  name, volume_name)
        request_urn = ('%s/id/%s@%s') % (
            FreeNASServer.REST_API_SNAPSHOT,
            urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/' + volume_name),
            name)
        LOG.debug('_delete_snapshot urn : %s', request_urn)
        try:
            ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                             request_urn, None)
            LOG.debug('_delete_snapshot select response : %s', json.dumps(ret))
            if ret['status'] == 'error' and ret['code'] == 404:
                LOG.info("Attempting delete Cinder volume %s snapshot %s, however it cannot be found on TrueNAS"
                         % (volume_name, name))
                LOG.info("Assume TrueNAS admin delete it manually, proceeding with snapshot delete action on cinder side")
                return
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)
        try:
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug('_delete_snapshot delete response : %s', json.dumps(ret))
            # When deleting volume with dependent snapsnot clone, 422 error triggered. Throw VolumeIsBusy exception ensures
            # upper stream cinder manager mark volume status available instead of error-deleting.
            if ret['status'] == 'error' and ret['code'] == 422:
                errorexception = exception.VolumeIsBusy(
                    _("Cannot delete volume when clone child volume or snapshot exists!"), volume_name=name)
                raise errorexception
            elif ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while deleting snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            if not isinstance(e, exception.VolumeIsBusy):
                raise FreeNASApiError('Unexpected error', e)

    def _create_volume_from_snapshot(self, name, snapshot_name,
                                     snap_zvol_name):
        """creates a volume from a snapshot"""
        args = {}
        args['snapshot'] = ('%s/%s@%s') % (
            self.configuration.ixsystems_dataset_path,
            snap_zvol_name,
            snapshot_name)
        args['dataset_dst'] = ('%s/%s') % (
            self.configuration.ixsystems_dataset_path, name)
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")
        request_urn = ('%s/%s') % (
            FreeNASServer.REST_API_SNAPSHOT, FreeNASServer.CLONE)
        LOG.debug('_create_volume_from_snapshot urn : %s', request_urn)
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            LOG.debug('_create_volume_from_snapshot response : %s',
                      json.dumps(ret))
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while creating snapshot: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def _promote_volume(self, volume_name):
        """Promote a volume"""
        request_urn = ('%s/id/%s/promote') % (
            FreeNASServer.REST_API_VOLUME,
            urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/' + volume_name))
        LOG.debug('_promote_volume urn : %s', request_urn)
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = ('Error while promoting volume: %s' % ret['response'])
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)

    def _is_service_project(self, project_id):
        # Use keystone api to check project_id is service project
        # Return True if it is service project, otherwise return False
        grp = cfg.OptGroup('keystone_authtoken')
        ops = [cfg.StrOpt('auth_url'), cfg.StrOpt('username'), cfg.StrOpt('password'),
               cfg.StrOpt('project_name'), cfg.StrOpt('user_domain_name'), cfg.StrOpt('project_domain_name')]
        CONF.register_group(grp)
        CONF.register_opts(ops, group=grp)
        auth = v3.Password(auth_url=CONF.keystone_authtoken.auth_url,
                           username=CONF.keystone_authtoken.username,
                           password=CONF.keystone_authtoken.password,
                           project_id=project_id,
                           user_domain_name=CONF.keystone_authtoken.user_domain_name,
                           project_domain_name=CONF.keystone_authtoken.project_domain_name)
        sess = session.Session(auth=auth)
        keystone = client.Client(session=sess)
        try:
            project = keystone.projects.get(project_id)
            if project.name == CONF.keystone_authtoken.project_name:
                return True
        except Exception:
            # Invalid project id will cause exeception from keystone client,
            # in this case it is allowed and normal, hence do nothing
            pass
        return False

    def _system_version(self):
        LOG.debug('_update_volume_stats start /system/version request')
        # Use API v2.0 /system/version to detect nasversion
        # API v2.0 /system/version available for FreeNAS 11.x TrueNAS 12.x TrueNAS 13.x TrueNAS Scale 22.x
        request_urn = ("/system/version")
        self.handle.set_api_version('v2.0')
        # For legacy verion that does not support API v2.0 /system/version return fallback value "VersionNotFound"
        versionresult = "VersionNotFound"
        try:
            versionret = self.handle.invoke_command(
                FreeNASServer.SELECT_COMMAND,
                request_urn, None)
            LOG.debug('_update_volume_stats start /system/version response: %s', versionret)
            versionresult = json.loads(versionret['response'])
            LOG.debug('_update_volume_stats /system/version response : %s', versionresult)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)
        finally:
            return str(versionresult)

    def _tunable(self):
        LOG.debug('_tunable /tunable request')
        request_urn = ("/tunable")
        self.handle.set_api_version('v2.0')
        tunableresult = []
        try:
            tunableret = self.handle.invoke_command(
                FreeNASServer.SELECT_COMMAND,
                request_urn, None)
            tunableresult = json.loads(tunableret['response'])
            LOG.debug('Tunable response : %s', tunableresult)
        except Exception as e:
            raise FreeNASApiError('Unexpected error', e)
        finally:
            return tunableresult

    def _update_volume_stats(self):
        data = {}
        nasversion = self._system_version()
        # Implementation for TrueNAS 12.0 upwards on API V2.0
        # If user are connecting to FreeNAS report error
        if nasversion.find("FreeNAS") >= 0:
            LOG.error("FreeNAS is no longer support by this version of cinder driver.")
            raise FreeNASApiError('Version not supported', 'FreeNAS is no longer support by this version of cinder driver.')
        elif nasversion == "VersionNotFound":
            LOG.error("TrueNAS not found")
            raise FreeNASApiError('TrueNAS not found')
        else:
            """Retrieve dataset available and used using API 2.0
            /pool/dataset/id/$id instead of API 1.0.
            This enable support for Truenas core/Truenas scale.
            REST API: $ GET /pool/dataset/id/$id retrive available and used parsed value
            for id matching config file 'ixsystems_dataset_path'
            """
            self.handle.set_api_version('v2.0')
            request_urn = ('%s%s') % ('/pool/dataset/id/', urllib.parse.quote_plus(self.configuration.ixsystems_dataset_path))
            ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND, request_urn, None)
            retresult = json.loads(ret['response'])
            avail = retresult['available']['parsed']
            used = retresult['used']['parsed']
            LOG.info('_update_volume_stats avail : %s', avail)
            LOG.info('_update_volume_stats used : %s', used)
            data["volume_backend_name"] = self.backend_name
            data["vendor_name"] = self.vendor_name
            data["driver_version"] = self.VERSION
            data["storage_protocol"] = self.storage_protocol
            data['total_capacity_gb'] = ix_utils.get_size_in_gb(avail+used)
            data['free_capacity_gb'] = ix_utils.get_size_in_gb(avail)
            data['reserved_percentage'] = (
                self.configuration.ixsystems_reserved_percentage)
            data['reserved_percentage'] = 0
            data['QoS_support'] = False

        self.stats = data
        return self.stats

    def _create_cloned_volume_to_snapshot_map(self, volume_name, snapshot):
        """maintain a mapping between cloned volume and tempary snapshot."""
        map_file = os.path.join(CONF.volumes_dir, volume_name)
        jparams = json.dumps(snapshot)
        try:
            fd = open(map_file, 'w+')
            fd.write(jparams)
            fd.close()
        except Exception as e:
            LOG.error('_create_halo_volume_name_map: %s', e)

    def _extend_volume(self, name, new_size):
        """Extend an existing volumes size."""
        LOG.debug('_extend__volume name: %s', name)
        params = {}
        params['volsize'] = ix_utils.get_bytes_from_gb(new_size)
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        request_urn = ('%s/id/%s') % (
            FreeNASServer.REST_API_VOLUME,
            urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/' + name))
        ret = self.handle.invoke_command(FreeNASServer.UPDATE_COMMAND,
                                         request_urn, jparams)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = ('Error while extending volume: %s' % ret['response'])
            raise FreeNASApiError('Unexpected error', msg)

    def _create_export(self, volume_name):
        freenas_volume = ix_utils.generate_freenas_volume_name(
            volume_name,
            self.configuration.ixsystems_iqn_prefix)

        if freenas_volume is None:
            LOG.error('Error in exporting FREENAS volume!')
            handle = None
        else:
            handle = "%s:%s,%s %s" % \
                     (self.configuration.ixsystems_server_hostname,
                      self.configuration.ixsystems_server_iscsi_port,
                      freenas_volume['target'],
                      freenas_volume['iqn'])

        LOG.debug('provider_location: %s', handle)
        return handle
