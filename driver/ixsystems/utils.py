#vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2016 iXsystems
import six
def get_size_in_gb(size_in_bytes):
    "convert size in gbs"
    return size_in_bytes/(1024*1024*1024)

def generate_truenas_volume_name(name, iqn_prefix):
    """Create TRUENAS volume / iscsitarget name from Cinder name."""
    backend_volume = 'volume-' + name.split('-')[1]
    backend_target = 'target-' + name.split('-')[1]
    backend_iqn = iqn_prefix + backend_target
    return {'name': backend_volume, 'target': backend_target, 'iqn': backend_iqn}

def generate_truenas_snapshot_name(name, iqn_prefix):
    """Create TRUENAS snapshot / iscsitarget name from Cinder name."""
    backend_snap = 'snap-' + name.split('-')[1]
    backend_target = 'target-' + name.split('-')[1]
    backend_iqn = iqn_prefix + backend_target
    return {'name': backend_snap, 'target': backend_target, 'iqn': backend_iqn}

def get_iscsi_portal(hostname, port):
    """Get iscsi portal info from iXsystems TRUENAS configuration."""
    return "%s:%s" % (hostname, port)
