Cinder Driver for iXsystems
===========

This repo contains driver scripts for openstack block storage manipulation project called Openstack Cinder. This cinder driver will use

* FreeNAS 9.3 / 9.10


Requirements 
===========
A system running FreeNAS 9.3 / 9.10, with at minimum 8GB of memory and a minimum 20GB Disk.
Another system running Devstack Kilo Release with following configuration

Minimal System Requirements
* RAM : 4 GB
* CPU : 4 Cores
* Disk : 40 GB


Getting Started
===========

Following are steps for using iXsystems Cinder driver.

```
% git clone --depth=1 https://github.com/iXsystems/
% cp -R ./cinder/driver/ixsystem/ /opt/stack/cinder/cinder/volume/drivers/
```

After following above steps, cinder driver need to be configured. open /etc/cinder/cinder.conf in any editor of your choice and add/edit the following parameters,

1. Edits - Edit following parameters in cinder.conf

 ```
 default_volume_type = ixsystems-iscsi  
 enabled_backends = ixsystems-iscsi, lvmdriver-1 
 ```
2. Additions - Add following parameters and their appropriate value in cinder.conf 

 ```
 [ixsystems-iscsi]
 iscsi_helper = <iscsi helper type. Standard Value>
 volume_dd_blocksize = <block size>
 volume_driver = <It is the path of main class of iXsystems cinder driver. Stardard Value for this driver is cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver>
 ixsystems_login = <username of TrueNAS Host>
 ixsystems_password = <Password of TrueNAS Host>
 ixsystems_server_hostname = <IP Address of TrueNAS Host>
 ixsystems_volume_backend_name = <driver specific information. Standard value is 'iXsystems_FREENAS_Storage' > 
 ixsystems_iqn_prefix = <Base name of ISCSI Target. (Get it from TrueNAS web UI in from following section : Sharing -> Block(iscsi) -> Target Global Configuration -> Base Name)>
 ixsystems_datastore_pool = <Create a dataset on TreeNAS host and assign dataset name here as a value e.g. 'cinder-zpool'>
 ixsystems_vendor_name = <driver specific information. Standard value is 'iXsystems' >
 ixsystems_storage_protocol =  <driver specific information. Standard value is 'iscsi'>
 ```

 Example is given bellow,

 ```
 [ixsystems-iscsi]
 iscsi_helper = tgtadm
 volume_dd_blocksize = 512
 volume_driver = cinder.volume.drivers.ixsystems.iscsi.FreeNASISCSIDriver
 ixsystems_login = root
 ixsystems_password = thisisdummypassword
 ixsystems_server_hostname = 10.3.1.81
 ixsystems_volume_backend_name = iXsystems_FREENAS_Storage
 ixsystems_iqn_prefix = iqn.2005-10.org.freenas.ctl
 ixsystems_datastore_pool = cinder-zpool
 ixsystems_vendor_name = iXsystems
 ixsystems_storage_protocol = iscsi
 ```


3. Restarting cinder service
 
 There are two ways to to restart cinder service with new cinder driver 

 1. Using screen command - 
   
   The `screen` Command is used to observe the running services. You can read documentation for `screen` here - (https://www.gnu.org/software/screen/manual/screen.html)
   
    Use following command to attach to devstack screens

    ```
    screen -x stack .
    ```

    Go to `c-vol` screen using screen command like options like `Ctrl-a p` to go to previous screen; `C-a p`

    Kill `C-vol` service using `Ctrl-c` command and press up arrow button and then Enter to restart cinder service. Now new edited cinder.conf file is read by cinder service. 
   
                                                    OR
   
 2. Using cinder service command
   
   Run following command to attach cinder service screen. After the command is run, existing cinder service screen is attached on terminal we will kill and restart the existing service.  
   
    ```
    /usr/local/bin/cinder-volume --config-file /etc/cinder/cinder.conf & echo $! >/opt/stack/status/stack/c-vol.pid; fg || echo "c-vol failed to start" | tee "/opt/stack/status/stack/c-vol.failure"
    ```
    Kill service using `Ctrl-c` command and press up arrow button and then Enter to restart cinder service. Now new edited cinder.conf file is read by cinder service.
   


Using iXsystems Cinder Driver
===========

Following are few example commands for using iXsystems Cinder driver-

To create volume -
$ cinder create --name <volumeName> <volumeSizeInGB>
Example
$ cinder create --name TestVolume 2

About Source Code
=================

iXsystems Cinder Driver contains following scripts -

* iscsi.py - Cinder APIs are defined here. For Example - create_volume, delete_volume etc.
* freenasapi.py - REST API Call routine is defined here and it contains all the methods necessary to do it.
* options.py - It defines default freenas configuration parameters if those are not fetched from cinder.conf file.


