TrueNAS Cinder Driver
=====================

This repository contains driver scripts for TrueNAS version >= 12.x interaction with OpenStack Cinder for block storage manipulation.

WARNING
==================

This driver should be considered experimental. Use at your own risk!

Requirements
============

1. A TrueNAS system with at least 8 Gb of memory and a minimum 20 GiB disk.  Suggested version >= 12.x to use API v2.0
2. Another system running either DevStack (Train or higher) or an OpenStack storage node.
3. This driver is now upgraded to Python 3, so is usable by OpenStack versions from Train on.  

Getting Started with Devstack
=============================

Download and install the TrueNAS Cinder driver on the system running Devstack Newton or newer release:

```
% sudo -s
# cd /
# git clone --depth=1 https://github.com/iXsystems/cinder
% su - stack
% cd /
% cp -R ./cinder/driver/ixsystems/ /opt/stack/cinder/cinder/volume/drivers/
```

Configure the Cinder driver. Open **/etc/cinder/cinder.conf** in an editor to both *edit* and *add* parameters.

**Edit these lines**:

 ```
 default_volume_type = ixsystems-iscsi
 enabled_backends = ixsystems-iscsi, lvm
 ```

**Add these parameters and the appropriate values**:

 ```
 [ixsystems-iscsi]
 iscsi_helper = <iscsi helper type. Standard Value>
 volume_dd_blocksize = <block size>
 volume_driver = <Path of the main class of iXsystems cinder driver. The standard value for this driver is cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver>
 ixsystems_login = <username of TrueNAS Host - currently needs to be root>
 ixsystems_password = <Password of TrueNAS Host - the root password>
 ixsystems_server_hostname = <IP Address of TrueNAS Host>
 ixsystems_volume_backend_name = <driver specific information. Standard value is 'iXsystems_TRUENAS_Storage' >
 ixsystems_iqn_prefix = <Base name of ISCSI Target. (Get it from the web UI of the connected TrueNAS system by navigating: Sharing -> Block(iscsi) -> Target Global Configuration -> Base Name)>
 ixsystems_datastore_pool = <Base pool name on the connected TrueNAS host e.g. 'tank'>
 ixsystems_dataset_path = <Dataset name inside the pool, full path including pool.  Can just be pool name for no nesting.  e.g. 'tank/os/cinder'.  This is where zvols will be created by the driver.>
 ixsystems_vendor_name = <driver specific information. Standard value is 'iXsystems' >
 ixsystems_storage_protocol =  <driver specific information. Standard value is 'iscsi'>
 ```

Here is an example configuration:

 ```
 [ixsystems-iscsi]
 iscsi_helper = tgtadm
 volume_dd_blocksize = 512
 volume_driver = cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver
 ixsystems_login = root
 ixsystems_password = thisisdummypassword
 ixsystems_server_hostname = 100.1.2.34
 ixsystems_volume_backend_name = iXsystems_TRUENAS_Storage
 ixsystems_iqn_prefix = iqn.2005-10.org.freenas.ctl
 ixsystems_datastore_pool = tank
 ixsystems_dataset_path = tank/openstack/cinder
 ixsystems_vendor_name = iXsystems
 ixsystems_storage_protocol = iscsi
 ```

Now restart the Cinder service to enable the changes. The simplest method is to reboot the Devstack system.

Alternatively, to restart the Cinder service manually without rebooting, use the `screen` command (documentation: https://www.gnu.org/software/screen/manual/screen.html). Attach to the devstack screens by following these steps:

```
% su -s
# script
# su - stack
% script
% screen -x stack .
```

Switch to the `c-vol` screen by holding `Ctrl` and pressing `A` and `P` in rapid sequence. Stop the `c-vol` service by pressing `Ctrl + C`.
Press the `Up Arrow` button then `Enter` to restart the Cinder service.
The edited **cinder.conf** is read by the Cinder service as it restarts.

After the initial reboot or manual reset of the Cinder service, it can be easily restarted with this command:

`/usr/local/bin/cinder-volume --config-file /etc/cinder/cinder.conf & echo $! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"`

After the Cinder service is restarted, log in to the web interface of the Devstack Newton system by navigating to the system IP address in a web browser. After logging in, navigate to `Admin -> System -> Volumes -> Volume Types` and click `Create Volume Type`. Type `ixsystems-iscsi` in the **Name** field and check the **Public** option. Create this volume type, which is added to the list of types after the system completes the task. 

Click Update Volume Type Metadata for the volume type you just created (example:ixsystems-iscsi). 
Add metadata with key=volume_backend_name value=iXsystems_TRUENAS_Storage (This value comes from cinder.conf ixsystems_volume_backend_name = iXsystems_TRUENAS_Storage)

Note: You can set your own Volume Type name.

Now the TrueNAS Cinder driver is functional in the OpenStack Web Interface.

Getting Started If You Are Using The OpenStack Installation Guide
=================================================================
If you are following the installation guide [here](https://docs.openstack.org/install-guide/), then after you have installed a storage node as in the documentation, take the following steps.

```
% sudo su -
# git clone --depth=1 https://github.com/iXsystems/cinder
# cp -R ./cinder/driver/ixsystems/ /usr/lib/python3/dist-packages/cinder/volume/drivers/
```

Configure the cinder driver as above in the DevStack instructions, starting with the editing of **/etc/cinder/cinder.conf**

Using the Cinder Driver
=======================

Here are some examples commands:

* Create a volume:

  `$ cinder create --name <volumeName> <volumeSizeInGiB>`

  Examples:

  `$ cinder create --name TestVolume 2`

  `$ openstack volume create --size 20 --image ubuntu-20.04 --description "Volume for test-vm" --bootable test-vm-vol` 

The `Projects -> Volumes` and `Admin -> Volumes` sections of the web interface integrate Cinder functionality directly in the interface options using the `ixsystems-iscsi` Volume Type.

Additional Notes
================
* It has been noted that for an initial connection to be made, the TrueNAS host needs to have a valid ssl certificate installed
and the key `ixsystems_server_hostname` in `cinder.conf` needs to be set to the FQDN referenced by the certificate.  This issue needs
more investigation.

* Users have reported that scaling beyond 80 LUNS is possible when setting the `kern.cam.ctl.max_ports=512` tunable in TrueNAS 13.

About Source Code
=================

The TrueNAS Cinder driver uses several scripts:

* **iscsi.py**: Defines the Cinder APIs, including `create_volume` and `delete_volume`.
* **truenasapi.py**: Defines the REST API call routine and methods.
* **options.py**: Defines the default configuration parameters not fetched from the **cinder.conf** file.
