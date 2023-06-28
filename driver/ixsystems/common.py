#  Copyright (c) 2016 iXsystems
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import urllib.parse
import simplejson as json

from cinder import exception
from cinder.i18n import _
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASApiError
from cinder.volume.drivers.ixsystems.freenasapi import FreeNASServer
from cinder.volume.drivers.ixsystems import utils as ix_utils
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneauth1.exceptions.http import Unauthorized
from keystoneclient.v3 import client
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class TrueNASCommon(object):
    """ TrueNAS cinder driver helper class, contains reusable TrueNAS specific driver logic"""
    VERSION = "2.0.0"
    IGROUP_PREFIX = 'openstack-'

    required_flags = ['ixsystems_transport_type',
                      'ixsystems_server_hostname',
                      'ixsystems_server_port',
                      'ixsystems_server_iscsi_port',
                      'ixsystems_volume_backend_name',
                      'ixsystems_vendor_name',
                      'ixsystems_storage_protocol',
                      'ixsystems_datastore_pool',
                      'ixsystems_dataset_path',
                      'ixsystems_iqn_prefix',]

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
        LOG.debug(f'Using iXsystems FREENAS server: {host_system}')
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

    def check_flags(self):
        """Check if any required iXsystems configuration flag is missing."""
        for flag in self.required_flags:
            if not getattr(self.configuration, flag, None):
                raise exception.CinderException(_(f'{flag} is not set'))

    def do_custom_setup(self):
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

    def create_volume(self, name, size):
        """Creates a volume of specified size."""
        params = {}
        params['name'] = self.configuration.ixsystems_dataset_path + '/' + name
        params['type'] = 'VOLUME'
        params['volsize'] = ix_utils.get_bytes_from_gb(size)
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        request_urn = f'{FreeNASServer.REST_API_VOLUME}'
        LOG.debug(f'_create_volume command : {FreeNASServer.CREATE_COMMAND}')
        LOG.debug(f'_create_volume urn : {request_urn}')
        LOG.debug(f'_create_volume params : {params}')
        ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                         request_urn, jparams)
        LOG.debug(f'_create_volume response : {json.dumps(ret)}')
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while creating volume: { ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

    def _target_to_extent(self, target_id, extent_id):
        """Create relationship between iscsi target to iscsi extent."""

        LOG.debug(f'_target_to_extent target id : {target_id}'\
        f'extend id : {extent_id}')

        request_urn = f'{FreeNASServer.REST_API_TARGET_TO_EXTENT}/'
        params = {}
        params['target'] = target_id
        params['extent'] = extent_id
        # params['iscsi_lunid'] = 0   # no longer needed with API v2.0
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')

        LOG.debug(f'_create_target_to_extent params : {json.dumps(params)}')

        tgt_ext = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jparams)

        LOG.debug(f'_target_to_extent response : {json.dumps(tgt_ext)}')

        if tgt_ext['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while creating relation between \
            target and extent: {tgt_ext["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

    def _create_target(self, name):
        """Create target"""
        # v2.0 API - targetgroup can now be added when target is created
        targetgroup_params = [{}]
        targetgroup_params[0]['portal'] = int(
            self.configuration.ixsystems_portal_id)

        targetgroup_params[0]['initiator'] = int(
            self.configuration.ixsystems_initiator_id)
        tgt_params = {}
        tgt_params['name'] = name
        tgt_params['groups'] = targetgroup_params
        jtgt_params = json.dumps(tgt_params)
        jtgt_params = jtgt_params.encode('utf8')
        LOG.debug(f'_create_target params : {json.dumps(tgt_params)}')
        request_urn = f'{FreeNASServer.REST_API_TARGET}/'
        target = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                            request_urn, jtgt_params)
        LOG.debug(f'_create_target response : {json.dumps(target)}')

        if target['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while creating iscsi target: {target["response"]}'
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
        vol_param = f'{self.configuration.ixsystems_dataset_path}/{volume_name}'
        ext_params['disk'] = 'zvol/' + vol_param
            
        jext_params = json.dumps(ext_params)
        LOG.debug(f'_create_extent params : {jext_params}')
        jext_params = jext_params.encode('utf8')
        request_urn = f'{FreeNASServer.REST_API_EXTENT}/'
        extent = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                            request_urn, jext_params)

        LOG.debug(f'_create_extent response : {json.dumps(extent)}')

        if extent['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while creating iscsi target extent: {extent["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

        return json.loads(extent['response'])['id']

    def get_iscsitarget_id(self, name):
        """get iscsi target id from target name."""

        request_urn = f'{FreeNASServer.REST_API_TARGET}'
        LOG.debug(f'get_iscsitarget_id request_urn : {request_urn}')
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug(f'get_iscsitarget_id response : {json.dumps(ret)}')
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while deleting iscsi target: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return next(item for item in resp
                    if item['name'] == name)['id']
        except StopIteration:
            return 0

    def get_tgt_ext_id(self, name):
        """Get target-extent mapping id from target name."""

        request_urn = f'{FreeNASServer.REST_API_TARGET_TO_EXTENT}'
        LOG.debug(f'get_tgt_ext_id urn : {request_urn}')
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug(f'get_tgt_ext_id response : {json.dumps(ret)}')
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while deleting iscsi target: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return next(item for item in resp
                    if item['target'] == name)['id']
        except StopIteration:
            return 0

    def get_extent_id(self, name):
        """Get Extent ID from Extent Name."""

        request_urn = f'{FreeNASServer.REST_API_EXTENT}'
        LOG.debug(f'get_extent_id urn : {request_urn}')
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug(f'get_extent_id response : {json.dumps(ret)}')
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while getting extent id: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        try:
            return next(item for item in resp
                    if item['name'] == name)['id']
        except StopIteration:
            return 0

    def create_iscsitarget(self, name, volume_name):
        """Creates a iSCSI target on specified volume OR snapshot.
        """

        # Create iscsi target for specified volume
        tgt_id = self._create_target(name)

        # Create extent for iscsi target for specified volume
        ext_id = self._create_extent(name, volume_name)

        # Create target to extent mapping for specified volume
        self._target_to_extent(tgt_id, ext_id)

    def delete_target_to_extent(self, tgt_ext_id):
        """Deletes specified iSCSI target extent."""        

    def delete_target(self, target_id):
        """Deletes iSCSI target."""        
        if target_id:
            request_urn = f'{FreeNASServer.REST_API_TARGET}/id/{target_id}'
            LOG.debug(f'delete_target urn : {request_urn}')
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug(f'delete_target response : {json.dumps(ret)}')
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = (
                    f'Error while deleting iscsi target: {ret["response"]}')
                raise FreeNASApiError('Unexpected error', msg)

    def delete_extent(self, extent_id):
        """Deletes iscsi extent."""        
        if extent_id:
            request_urn = (f'{FreeNASServer.REST_API_EXTENT}/id/{extent_id}')
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug(f'delete_extent response : {json.dumps(ret)}')
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = 'Error while deleting iscsi extent: {ret["response"]}'
                raise FreeNASApiError('Unexpected error', msg)

    def delete_iscsitarget(self, name):
        """Deletes specified iSCSI target."""
        tgt_ext_id = self.get_tgt_ext_id(name)
        target_id = self.get_iscsitarget_id(name)
        extent_id = self.get_extent_id(name)

        self.delete_target_to_extent(tgt_ext_id)
        self.delete_target(target_id)
        self.delete_extent(extent_id)

    def _dependent_clone(self, name):
        """returns the fullname of snapshot used to create volume 'name'."""
        encoded_datapath = urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/')
        request_urn = f'{FreeNASServer.REST_API_VOLUME}'\
        f'/id/{encoded_datapath}{name}'
        LOG.debug(f'_dependent_clones urn : {request_urn}')
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                         request_urn, None)
        LOG.debug(f'_dependent_clones response : {json.dumps(ret)}')
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while getting volume: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)
        uresp = ret['response']
        resp = json.loads(uresp.decode('utf8'))
        return resp['origin']['value']

    def delete_volume(self, name):
        """Deletes specified volume."""
        encoded_datapath = urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/')
        request_urn = (f'{FreeNASServer.REST_API_VOLUME}'\
                       f'/id/{encoded_datapath}{name}')
        LOG.debug(f'_delete_volume urn : {request_urn}')
        # add check for dependent clone, if exists will delete
        clone = self._dependent_clone(name)
        ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                         request_urn, None)
        LOG.debug(f'_delete_volume response : {json.dumps(ret)}')

        # delete the cloned-from snapshot.
        # Must check before deleting volume, but delete snapshot after
        if clone:
            fullvolume, snapname = clone.split('@')
            temp, snapvol = fullvolume.rsplit('/', 1)
            self.delete_snapshot(snapname, snapvol)

        # When deleting volume with dependent snapsnot clone, 422 error
        # triggered. Throw VolumeIsBusy exception ensures upper stream
        # cinder manager mark volume status available instead of
        # error-deleting.
        if ret['status'] == 'error' and ret['code'] == 422:
            errorexception = exception.VolumeIsBusy(
                _("Cannot delete volume when clone child volume or snapshot exists!"),
                volume_name=name)
            raise errorexception
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while deleting volume: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

    def create_snapshot(self, name, volume_name):
        """Creates a snapshot of specified volume."""
        args = {}
        args['dataset'] = f'{self.configuration.ixsystems_dataset_path}/'\
                        f'{volume_name}'
        args['name'] = name
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")
        request_urn = f'{FreeNASServer.REST_API_SNAPSHOT}'
        LOG.debug('f_create_snapshot urn : {request_urn}')

        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            LOG.debug(f'_create_snapshot response : {json.dumps(ret)}')
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = f'Error while creating snapshot: {ret["response"]}'
                raise FreeNASApiError('Unexpected error', msg)
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error

    def delete_snapshot(self, name, volume_name):
        """Delets a snapshot of specified volume."""
        LOG.debug(f'_delete_snapshot, deleting name: {name} from '\
                f'volume: {volume_name}')
        encoded_datapath = urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/' + volume_name)
        request_urn = f'{FreeNASServer.REST_API_SNAPSHOT}'\
                f'/id/{encoded_datapath}@{name}'
        LOG.debug(f'_delete_snapshot urn : {request_urn}')
        try:
            ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                             request_urn, None)
            LOG.debug(f'_delete_snapshot select response : {json.dumps(ret)}')
            if ret['status'] == 'error' and ret['code'] == 404:
                LOG.info(f'Attempting delete Cinder volume {volume_name} '\
                f'snapshot {name}, however it cannot be found on TrueNAS')
                LOG.info('Assume TrueNAS admin delete it manually, '\
                'proceeding with snapshot delete action on cinder side')
                return
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error
        try:
            ret = self.handle.invoke_command(FreeNASServer.DELETE_COMMAND,
                                             request_urn, None)
            LOG.debug(f'_delete_snapshot delete response : {json.dumps(ret)}')
            # When deleting volume with dependent snapsnot clone, 422 error
            # triggered. Throw VolumeIsBusy exception ensures upper stream
            # cinder manager mark volume status available instead of
            # error-deleting.
            if ret['status'] == 'error' and ret['code'] == 422:
                errorexception = exception.VolumeIsBusy(
                    _('Cannot delete volume when clone child volume or \
                    snapshot exists!'), volume_name=name)
                raise errorexception
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = (f'Error while deleting snapshot: {ret["response"]}')
                raise FreeNASApiError('Unexpected error', msg)
        except Exception as exp:
            if not isinstance(exp, exception.VolumeIsBusy):
                raise FreeNASApiError('Unexpected error', exp) from exp

    def create_volume_from_snapshot(self, name, snapshot_name,
                                    snap_zvol_name):
        """creates a volume from a snapshot"""
        args = {}
        args['snapshot'] = f'{self.configuration.ixsystems_dataset_path}'\
            f'/{snap_zvol_name}@{snapshot_name}'
        args['dataset_dst'] = f'{self.configuration.ixsystems_dataset_path}'\
            f'/{name}'
        jargs = json.dumps(args)
        jargs = jargs.encode("utf8")
        request_urn = f'{FreeNASServer.REST_API_SNAPSHOT}'\
            f'/{FreeNASServer.CLONE}'
        LOG.debug(f'_create_volume_from_snapshot urn : {request_urn}')
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, jargs)
            LOG.debug(f'_create_volume_from_snapshot response : '\
                f'{json.dumps(ret)}')
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = f'Error while creating snapshot: {ret["response"]}'
                raise FreeNASApiError('Unexpected error', msg)
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error

    def promote_volume(self, volume_name):
        """Promote a volume"""
        encoded_datapath = urllib.parse.quote_plus(
            self.configuration.ixsystems_dataset_path + "/" + volume_name)
        request_urn = (f'{FreeNASServer.REST_API_VOLUME}/id/'\
            f'{encoded_datapath}/promote')
        LOG.debug(f'_promote_volume urn : {request_urn}')
        try:
            ret = self.handle.invoke_command(FreeNASServer.CREATE_COMMAND,
                                             request_urn, None)
            if ret['status'] != FreeNASServer.STATUS_OK:
                msg = (f'Error while promoting volume: {ret["response"]}')
                raise FreeNASApiError('Unexpected error', msg)
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error

    def is_service_project(self, project_id):
        """ Use keystone api to check project_id is service project
        Return True if it is service project, otherwise return False
        """
        grp = cfg.OptGroup('keystone_authtoken')
        ops = [cfg.StrOpt('auth_url'),
               cfg.StrOpt('username'),
               cfg.StrOpt('password'),
               cfg.StrOpt('project_name'),
               cfg.StrOpt('user_domain_name'),
               cfg.StrOpt('project_domain_name')]
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
        except Unauthorized:
            # Invalid project id will cause Forbidden exception from keystone client,
            # in this case it is allowed and normal, hence do nothing
            pass
        return False

    def system_version(self):
        """ Use API v2.0 /system/version to detect nasversion
        API v2.0 /system/version available for FreeNAS 11.x
        TrueNAS 12.x TrueNAS 13.x TrueNAS Scale 22.x
        """
        LOG.debug('update_volume_stats start /system/version request')
        request_urn = ("/system/version")
        self.handle.set_api_version('v2.0')
        # For legacy verion that does not support API v2.0 /system/version
        # return fallback value "VersionNotFound"
        versionresult = "VersionNotFound"
        try:
            versionret = self.handle.invoke_command(
                FreeNASServer.SELECT_COMMAND,
                request_urn, None)
            LOG.debug(f'update_volume_stats start /system/version response: {versionret}')
            versionresult = json.loads(versionret['response'])
            LOG.debug(f'update_volume_stats /system/version response : {versionresult}')
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error
        finally:
            return str(versionresult)

    def tunable(self):
        """ Get tunable from TrueNAS"""
        LOG.debug('tunable /tunable request')
        request_urn = ("/tunable")
        self.handle.set_api_version('v2.0')
        tunableresult = []
        try:
            tunableret = self.handle.invoke_command(
                FreeNASServer.SELECT_COMMAND,
                request_urn, None)
            tunableresult = json.loads(tunableret['response'])
            LOG.debug(f'Tunable response : {tunableresult}')
        except FreeNASApiError as api_error:
            raise FreeNASApiError('Unexpected error', api_error) from api_error
        finally:
            return tunableresult

    def update_volume_stats(self):
        """Update volume stats"""
        data = {}
        nasversion = self.system_version()
        # Implementation for TrueNAS 12.0 upwards on API V2.0
        # If user are connecting to FreeNAS report error
        if nasversion.find("FreeNAS") >= 0:
            LOG.error("FreeNAS is no longer support by this version of \
            cinder driver.")
            raise FreeNASApiError('Version not supported',
                'FreeNAS is no longer support by this version of cinder driver.')
        if nasversion == "VersionNotFound":
            LOG.error("TrueNAS not found")
            raise FreeNASApiError('TrueNAS not found')
        """Retrieve dataset available and used using API 2.0
        /pool/dataset/id/$id instead of API 1.0.
        This enable support for Truenas core/Truenas scale.
        REST API: $ GET /pool/dataset/id/$id retrive available
        and used parsed value for id matching config file 
        'ixsystems_dataset_path'
        """
        self.handle.set_api_version('v2.0')
        encoded_datapath = urllib.parse.quote_plus(
            self.configuration.ixsystems_dataset_path)
        request_urn = f'/pool/dataset/id/{encoded_datapath}'
        ret = self.handle.invoke_command(FreeNASServer.SELECT_COMMAND,
                                            request_urn, None)
        retresult = json.loads(ret['response'])
        avail = retresult['available']['parsed']
        used = retresult['used']['parsed']
        LOG.info(f'update_volume_stats avail : {avail}')
        LOG.info(f'update_volume_stats used : {used}')
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

    def extend_volume(self, name, new_size):
        """Extend an existing volumes size."""
        LOG.debug(f'_extend__volume name: {name}')
        params = {}
        params['volsize'] = ix_utils.get_bytes_from_gb(new_size)
        jparams = json.dumps(params)
        jparams = jparams.encode('utf8')
        encoded_datapath = urllib.parse.quote_plus(
                self.configuration.ixsystems_dataset_path + '/' + name)
        request_urn = f'{FreeNASServer.REST_API_VOLUME}/id/{encoded_datapath}'

        ret = self.handle.invoke_command(FreeNASServer.UPDATE_COMMAND,
                                         request_urn, jparams)
        if ret['status'] != FreeNASServer.STATUS_OK:
            msg = f'Error while extending volume: {ret["response"]}'
            raise FreeNASApiError('Unexpected error', msg)

    def create_export(self, volume_name):
        """Create export from volume name"""        
        freenas_volume = ix_utils.generate_freenas_volume_name(
            volume_name,
            self.configuration.ixsystems_iqn_prefix)

        if freenas_volume is None:
            LOG.error('Error in exporting FREENAS volume!')
            handle = None
        else:
            handle = f'{self.configuration.ixsystems_server_hostname}:'\
            f'{self.configuration.ixsystems_server_iscsi_port},'\
            f'{freenas_volume["target"]} {freenas_volume["iqn"]}'
        LOG.debug(f'provider_location: {handle}')
        return handle
