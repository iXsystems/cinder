Cinder Driver for iXsystems
===========================

This repo contains driver scripts for the OpenStack block storage manipulation project called OpenStack Cinder.
The Cinder driver uses:

* FreeNAS 9.3 / 9.10


Requirements
============

1. A system running FreeNAS 9.3 / 9.10 with at least 8 Gb of memory and a minimum 20 Gb disk.
2. Another system running Devstack Kilo Release with this configuration:

   Minimal System Requirements:

   * RAM : 4 Gb
   * CPU : 4 Cores
   * Disk : 40 Gb


Getting Started
===============

Here are the initial steps for using the iXsystems Cinder driver:

```
% git clone --depth=1 https://github.com/iXsystems/cinder
% cp -R ./cinder/driver/ixsystems/ /opt/stack/cinder/cinder/volume/drivers/
```

After following these steps, the Cinder driver needs to be configured.
Open **/etc/cinder/cinder.conf** in an editor and add or edit these parameters, then restart the service to enable the changes:

1. Edits - Edit these lines in **cinder.conf**:

 ```
 default_volume_type = ixsystems-iscsi
 enabled_backends = ixsystems-iscsi, lvmdriver-1
 ```
 
2. Additions - Add these parameters and the appropriate values in **cinder.conf**:

 ```
 [ixsystems-iscsi]
 iscsi_helper = <iscsi helper type. Standard Value>
 volume_dd_blocksize = <block size>
 volume_driver = <It is the path of main class of iXsystems cinder driver. Stardard Value for this driver is cinder.volume.drivers.ixsystems.iscsi.TrueNASISCSIDriver>
 ixsystems_login = <username of TrueNAS Host>
 ixsystems_password = <Password of TrueNAS Host>
 ixsystems_server_hostname = <IP Address of TrueNAS Host>
 ixsystems_volume_backend_name = <driver specific information. Standard value is 'iXsystems_TRUENAS_Storage' >
 ixsystems_iqn_prefix = <Base name of ISCSI Target. (Get it from TrueNAS web UI in from following section : Sharing -> Block(iscsi) -> Target Global Configuration -> Base Name)>
 ixsystems_datastore_pool = <Create a dataset on TreeNAS host and assign dataset name here as a value e.g. 'cinder-zpool'>
 ixsystems_vendor_name = <driver specific information. Standard value is 'iXsystems' >
 ixsystems_storage_protocol =  <driver specific information. Standard value is 'iscsi'>
 ```

Here is an example configuration:

 ```
 [ixsystems-iscsi]
 iscsi_helper = tgtadm
 volume_dd_blocksize = 512
 volume_driver = cinder.volume.drivers.ixsystems.iscsi.TrueNASISCSIDriver
 ixsystems_login = root
 ixsystems_password = thisisdummypassword
 ixsystems_server_hostname = 10.3.1.81
 ixsystems_volume_backend_name = iXsystems_TRUENAS_Storage
 ixsystems_iqn_prefix = iqn.2005-10.org.truenas.ctl
 ixsystems_datastore_pool = cinder-zpool
 ixsystems_vendor_name = iXsystems
 ixsystems_storage_protocol = iscsi
 ```

3. Restart the Cinder service

   There are two ways to to restart the Cinder service with the new Cinder driver:

   1. Use the `screen` command:
   
      The `screen` command is used to observe the running services.
      Here is documentation for `screen`: (https://www.gnu.org/software/screen/manual/screen.html)
   
      Use this command to attach to the devstack screens:

      ```
      screen -x stack .
      ```

      Go to the `c-vol` screen using `screen` command options like `Ctrl-a p` to go to the previous screen.

      Kill the `C-vol` service using `Ctrl-c` and press the **up arrow** button and **Enter** to restart the Cinder service.
      The edited **cinder.conf** is read by the Cinder service as it restarts.

                                                    **OR**

   2. Use the `cinder service` command:

      Run the following command to attach cinder service screen.
      After the command is run, the existing Cinder service screen is attached on a terminal.
      Then terminate and restart the existing service.

      ```
      /usr/local/bin/cinder-volume --config-file /etc/cinder/cinder.conf & echo $! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"
      ```
      
      Disable the service using `Ctrl-c`.
      Press **up arrow** and then **Enter** to restart the Cinder service.
      The edited **cinder.conf** file is read by Cinder service during the restart.


Using the iXsystems Cinder Driver
=================================

Here are some examples commands that use the iXsystems Cinder driver:

* Create a volume:

  `$ cinder create --name <volumeName> <volumeSizeInGB>`

  Example:

  `$ cinder create --name TestVolume 2`


About Source Code
=================

The iXsystems Cinder driver uses several scripts:

* **iscsi.py**: Cinder APIs are defined here. Examples: `create_volume`, `delete_volume`, etc.
* **freenasapi.py**: The REST API call routine is defined here and it contains all necessary methods.
* **options.py**: Defines the default FreeNAS configuration parameters if not fetched from the **cinder.conf** file.
