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
from cinder.volume.drivers.ixsystems import common
from cinder.volume import volume_utils
from cinder.volume.drivers.ixsystems import utils as ix_utils
from cinder.i18n import _
from lxml import etree
import os
from oslo_config import cfg
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
        LOG.info('iXsystems: Init Cinder Driver')
        super(FreeNASISCSIDriver, self).__init__(*args, **kwargs)
        self.configuration.append_config_values(ixsystems_connection_opts)
        self.configuration.append_config_values(ixsystems_basicauth_opts)
        self.configuration.append_config_values(ixsystems_transport_opts)
        self.configuration.append_config_values(ixsystems_provisioning_opts)
        self.configuration.ixsystems_iqn_prefix += ':'
        self.common = common.TrueNASCommon(configuration=self.configuration)
        self.stats = {}


    def check_for_setup_error(self):
        """Check for iXsystems FREENAS configuration parameters."""
        LOG.info('iXSystems: Check For Setup Error')
        self.common._check_flags()

    def do_setup(self, context):
        """Setup iXsystems FREENAS driver
            Check for configuration flags and setup iXsystems FREENAS client
        """
        LOG.info('iXsystems Do Setup')
        #TODO:add check to see if volume exist, able to connect
        #truenas array
        self.check_for_setup_error()
        self.common._do_custom_setup()

    def create_volume(self, volume):
        """Creates a volume of specified size and export it as iscsi target."""
        LOG.info('iXsystems Create Volume')
        LOG.debug('create_volume : volume name :: %s', volume['name'])

        freenas_volume = ix_utils.generate_freenas_volume_name(volume['name'],
						self.configuration.ixsystems_iqn_prefix)
        
        LOG.debug('volume name after freenas generate : %s', json.dumps(freenas_volume))

        freenas_volume['size'] = volume['size']
        freenas_volume['target_size'] = volume['size']

        self.common._create_volume(freenas_volume['name'], freenas_volume['size'])
        #Remove LUN Creation from here,check at initi
        self.common._create_iscsitarget(freenas_volume['target'], 
                                        freenas_volume['name'])


    def delete_volume(self, volume):
        """Deletes volume and corresponding iscsi target."""
        LOG.info('iXsystems Delete Volume')
        LOG.debug('delete_volume %s', volume['name'])

        freenas_volume = ix_utils.generate_freenas_volume_name(volume['name'], self.configuration.ixsystems_iqn_prefix)

        if freenas_volume['target']:
            self.common._delete_iscsitarget(freenas_volume['target'])
        if freenas_volume['name']:
            self.common._delete_volume(freenas_volume['name'])


    def create_export(self, context, volume, connector):
        """Driver entry point to get the export info for a new volume."""
        LOG.info('iXsystems Create Export')
        LOG.debug('create_export %s', volume['name'])

        handle = self.common._create_export(volume['name'])
        LOG.info('provider_location: %s', handle)
        return {'provider_location': handle}

    def ensure_export(self, context, volume):
        """Driver entry point to get the export info for an existing volume."""
        LOG.info('iXsystems Ensure Export')
        LOG.debug('ensure_export %s', volume['name'])

        handle = self.common._create_export(volume['name'])
        LOG.info('provider_location: %s', handle)
        return {'provider_location': handle}

    def remove_export(self, context, volume):
        """Driver exntry point to remove an export for a volume.
            we have nothing to do for unexporting.
        """
        pass

    def initialize_connection(self, volume, connector):
        """Driver entry point to attach a volume to an instance."""
        LOG.info('iXsystems Initialise Connection')
        freenas_volume = ix_utils.generate_freenas_volume_name(volume['name'],self.configuration.ixsystems_iqn_prefix)
        if not freenas_volume['name']:
            # is this snapshot?
            freenas_volume = ix_utils.generate_freenas_snapshot_name(volume['name'],self.configuration.ixsystems_iqn_prefix)

        LOG.info('initialize_connection Entry: %s \t %s', volume['name'], connector['host'])
        properties = {}
        properties['target_discovered'] = False
        properties['target_portal'] = ix_utils.get_iscsi_portal(self.configuration.ixsystems_server_hostname,
						self.configuration.ixsystems_server_iscsi_port)
        properties['target_iqn'] = freenas_volume['iqn']
        properties['volume_id'] = volume['id']
        
        LOG.debug('initialize_connection data: %s', properties)
        return {'driver_volume_type': 'iscsi', 'data': properties}

    def terminate_connection(self, volume, connector, **kwargs):
        """Driver entry point to detach a volume from an instance."""
        pass

    def create_snapshot(self, snapshot):
        """Driver entry point for creating a snapshot."""
        LOG.info('iXsystems Create Snapshot')
        LOG.debug('create_snapshot %s', snapshot['name'])
        
        freenas_snapshot = ix_utils.generate_freenas_snapshot_name(snapshot['name'], self.configuration.ixsystems_iqn_prefix)
        freenas_volume = ix_utils.generate_freenas_volume_name(snapshot['volume_name'], self.configuration.ixsystems_iqn_prefix)

        self.common._create_snapshot(freenas_snapshot['name'], freenas_volume['name'])

    def delete_snapshot(self, snapshot):
        """Driver entry point for deleting a snapshot."""
        LOG.info('iXsystems Delete Snapshot')
        LOG.debug('delete_snapshot %s', snapshot['name'])
        freenas_snapshot = ix_utils.generate_freenas_snapshot_name(snapshot['name'],self.configuration.ixsystems_iqn_prefix)
        freenas_volume = ix_utils.generate_freenas_volume_name(snapshot['volume_name'],self.configuration.ixsystems_iqn_prefix)
        
        self.common._delete_snapshot(freenas_snapshot['name'], freenas_volume['name'])
    
    def create_volume_from_snapshot(self, volume, snapshot):
        """Creates a volume from snapshot."""
        LOG.info('iXsystems Craete Volume From Snapshot')
        LOG.info('create_volume_from_snapshot %s', snapshot['name'])

        existing_vol = ix_utils.generate_freenas_volume_name(snapshot['volume_name'],self.configuration.ixsystems_iqn_prefix)
        freenas_snapshot = ix_utils.generate_freenas_snapshot_name(snapshot['name'],self.configuration.ixsystems_iqn_prefix)
        freenas_volume = ix_utils.generate_freenas_volume_name(volume['name'],self.configuration.ixsystems_iqn_prefix)
        freenas_volume['size'] = volume['size']
        freenas_volume['target_size'] = volume['size']

        self.common._create_volume_from_snapshot(freenas_volume['name'], freenas_snapshot['name'], existing_vol['name'])
        self.common._create_iscsitarget(freenas_volume['target'],
                                        freenas_volume['name'])


    def get_volume_stats(self, refresh=False):
        """Get stats info from volume group / pool."""
        LOG.info('iXsystems Get Volume Status')
        if refresh:
            self.stats = self.common._update_volume_stats()
        LOG.info('get_volume_stats: %s', self.stats)
        return self.stats


    def create_cloned_volume(self, volume, src_vref):
        """Creates a volume from source volume."""
        LOG.info('iXsystems Create Colened Volume')
        LOG.info('create_cloned_volume: %s', src_vref['id'])

        context = None
        temp_snapshot = {'volume_name': src_vref['name'],
                         'name': 'name-c%s' % src_vref['id']}
        
        self.create_snapshot(temp_snapshot)
        self.create_volume_from_snapshot(volume, temp_snapshot)
        self.delete_snapshot(temp_snapshot)

    def extend_volume(self, volume, new_size):
        """Driver entry point to extend an existing volumes size."""
        LOG.info('iXsystems Extent Volume')
        LOG.info('extend_volume %s', volume['name'])
        
        freenas_volume = ix_utils.generate_freenas_volume_name(volume['name'],self.configuration.ixsystems_iqn_prefix) 
        freenas_new_size = new_size
        
        if volume['size'] != freenas_new_size:
            self.common._extend_volume(freenas_volume['name'], freenas_new_size)
