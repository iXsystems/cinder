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


def get_size_in_gb(size_in_bytes):
    """convert size in gbs"""
    return size_in_bytes / (1024 * 1024 * 1024)


def get_bytes_from_gb(size_in_gb):
    """Convert size from GB into bytes."""
    return size_in_gb * (1024 * 1024 * 1024)


def generate_freenas_volume_name(name, iqn_prefix):
    """Create FREENAS volume / iscsitarget name from Cinder name."""
    backend_volume = 'volume-' + name.split('-')[1]
    backend_target = 'target-' + name.split('-')[1]
    backend_iqn = iqn_prefix + backend_target
    return {'name': backend_volume,
            'target': backend_target, 'iqn': backend_iqn}


def generate_freenas_snapshot_name(name, iqn_prefix):
    """Create FREENAS snapshot / iscsitarget name from Cinder name."""
    backend_snap = 'snap-' + name.split('-')[1]
    backend_target = 'target-' + name.split('-')[1]
    backend_iqn = iqn_prefix + backend_target
    return {'name': backend_snap,
            'target': backend_target, 'iqn': backend_iqn}


def get_iscsi_portal(hostname, port):
    """Get iscsi portal info from iXsystems FREENAS configuration."""
    return "%s:%s" % (hostname, port)


def parse_truenas_version(version):
    """Parse and return TrueNAS verion from api to Tuple in ('FreeNAS'/'TrueNAS",'12.0'/'13.0'/'22.0','U2'/'U3') format"""
    vsplit = version.split('-')
    if len(vsplit) == 3:
        main = vsplit[0]
        mainversion = vsplit[1]
        patch = vsplit[2]
        return (main, mainversion, patch)
    if len(vsplit) == 2:
        main = vsplit[0]
        mainversion = vsplit[1]
        return (main, mainversion, '')
    return ('VersionNotFound', '0', '')
