Cinder Driver for iXsystems
===========================

This repo contains driver scripts for the OpenStack block storage manipulation project called OpenStack Cinder.
The Cinder driver is used only with TrueNAS.


Requirements
============

1. A system running TrueNAS with at least 8 Gb of memory and a minimum 20 Gib disk.
2. Another system running the Devstack Newton Release with this configuration:

   Minimal System Requirements:

   * RAM : 4 Gb
   * CPU : 4 Cores
   * Disk : 40 Gib


Getting Started
===============

Here are the initial steps to download and install the iXsystems Cinder driver on the system with Devstack Newton:

```
% sudo -s
# cd /
# git clone --depth=1 https://github.com/iXsystems/cinder
% su - stack
% cd /
% cp -R ./cinder/driver/ixsystems/ /opt/stack/cinder/cinder/volume/drivers/
```

Now the Cinder driver needs to be configured.

Open **/etc/cinder/cinder.conf** in an editor to both *edit* and *add* parameters, then restart the `cinder service` to enable the changes:

**Edits**: Edit these lines in **cinder.conf**:

 ```
 default_volume_type = ixsystems-iscsi
 enabled_backends = ixsystems-iscsi, lvmdriver-1
 ```

**Additions**: Add these parameters and the appropriate values in **cinder.conf**:

 ```
 [ixsystems-iscsi]
 iscsi_helper = <iscsi helper type. Standard Value>
 volume_dd_blocksize = <block size>
 volume_driver = <Path of the main class of iXsystems cinder driver. The standard value for this driver is cinder.volume.drivers.ixsystems.iscsi.TrueNASISCSIDriver>
 ixsystems_login = <username of TrueNAS Host>
 ixsystems_password = <Password of TrueNAS Host>
 ixsystems_server_hostname = <IP Address of TrueNAS Host>
 ixsystems_volume_backend_name = <driver specific information. Standard value is 'iXsystems_TRUENAS_Storage' >
 ixsystems_iqn_prefix = <Base name of ISCSI Target. (Get it from the web UI of the connected TrueNAS system by navigating: Sharing -> Block(iscsi) -> Target Global Configuration -> Base Name)>
 ixsystems_datastore_pool = <Create a dataset on the connected TreeNAS host and assign the dataset name here as a value. e.g. 'cinder-tank'>
 ixsystems_vendor_name = <driver specific information. Standard value is 'iXsystems' >
 ixsystems_storage_protocol =  <driver specific information. Standard value is 'iscsi'>
 ```

Here is an example configuration:

 ```
 [ixsystems-iscsi]
 iscsi_helper = tgtadm
 volume_dd_blocksize = 512
 volume_driver = cinder.volume.drivers.ixsystems.iscsi.FREENASISCSIDriver
 ixsystems_login = root
 ixsystems_password = thisisdummypassword
 ixsystems_server_hostname = 100.1.2.34
 ixsystems_volume_backend_name = iXsystems_FREENAS_Storage
 ixsystems_iqn_prefix = iqn.2005-10.org.freenas.ctl
 ixsystems_datastore_pool = cinder-tank
 ixsystems_vendor_name = iXsystems
 ixsystems_storage_protocol = iscsi
 ```

Now restart the Cinder service. The simplest method is to reboot the Devstack Newton system.
Alternatively, the Cinder service can be restarted manually.

To reset the Cinder service manually without rebooting, use the `screen` command (documentation: https://www.gnu.org/software/screen/manual/screen.html).
Attach to the devstack screens by following these steps:

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

After the first reboot or manual reset of the Cinder service, it can be more easily restarted with this command:

`/usr/local/bin/cinder-volume --config-file /etc/cinder/cinder.conf & echo $! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"`

After the Cinder service is restarted, log in to the web interface of the Devstack Newton system by navigating to the system IP address in a web browser. After logging in, navigate to `Admin -> System -> Volumes -> Volume Types` and click `Create Volume Type`. Type `ixsystems-iscsi` in the **Name** field and check the **Public** option. Create this volume type, which is added to the list of types after the system completes the task. Now the iXsystems Cinder driver is functional in the OpenStack Web Interface.

Using the iXsystems Cinder Driver
=================================

Here are some examples commands that use the iXsystems Cinder driver:

* Create a volume:

  `$ cinder create --name <volumeName> <volumeSizeInGiB>`

  Example:

  `$ cinder create --name TestVolume 2`

The `Projects -> Volumes` and `Admin -> Volumes` sections of the web interface integrate Cinder functionality directly in the interface options using the `ixsystems-iscsi` Volume Type.

About Source Code
=================

The iXsystems Cinder driver uses several scripts:

* **iscsi.py**: Cinder APIs are defined here. Examples: `create_volume`, `delete_volume`, etc.
* **truenasapi.py**: The REST API call routine is defined here and it contains all necessary methods.
* **options.py**: Defines the default TrueNAS configuration parameters if not fetched from the **cinder.conf** file.
