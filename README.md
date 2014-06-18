fiorun
======

A python script to launch many fio bench.

It can be used to create a logical drive, create a new partition or reformat the partition.

Actually, only HP's smart array logical drive are supported for hardware raid, help is welcome.

It only runs on linux.

It take a yaml file as an argument that describes the step to execute.

After the execution a image and a csv is produced with values.

The image shows an heat map with response time and plot the bandwith or io/s.

The sections for the yaml file are :

* defaults, to describe common values
  
  each command will look in the defaults for the missing arguments. Every default value can be change on the command line with -D key=value

* variables, some variables used in the fio script, see description latter
* plot, to describe the output image
* csv, to describe the output csv
* run, the steps to execute.

A simple yaml look likes :

    defaults:
        blockdevice: "/dev/sdb"
        mount_point: "/bench"
        part: "/dev/sdb"
        fio: "/opt/bench/fio-2.1.4/fio"
        fio_script: "test.fio"
        fio_dir: "/bench/fio"
        count: 3
    plot:
      mode: bw
      filename: /opt/bench/test.png
    csv:
      filename: /opt/bench/test.csv
    run:
      - do_part:
    # simple fs
      - do_fs_xfs:
      - do_mount_xfs:
      - do_fio:
          label: "A"
    # unaligned and log device
      - do_fs_xfs:
          logdev: "/dev/sdc"
      - do_mount_xfs:
          logdev: "/dev/cciss/c0d2"
      - do_fio:
          label: "B"

Installation
============

It needs matplotlib and PyYAML.

So to build an python virtual env with latest dependencies version, on a Redhat, one can run :

    yum-builddep python-matplotlib numpy PyYAML
    yum install python-virtualenv
    cd /opt/bench
    virtualenv pybench
    pybench/bin/pip install matplotlib
    pybench/bin/pip install PyYAML

Actions
=======

* modify_cciss

  apply a modification on a HP's SmartArray controler

   * object (mandatory): either ctrl or ld, will apply the modification on the controler or the logicial drive
   * command (mandatory): the modify command to execute
   * slot: the slot to identify the controler
   * ld: the logical drive

* do_cciss_ld

  create a logical drive on a HP's SmartArray.

   * slot (mandatory): the slot to identify the controler
   * ld (mandatory): the logical drive

* wait_cciss_ld

  Wait for HP's SmartArray logical drive to be ready after a RAID creation.

   * slot (mandatory): the slot to identify the controler
   * ld (mandatory): the logical drive

* do_part

  Create a partition on a block device. If stripsize and stripcount are given, cylinder size
  will be stripsize * stripcount.

   * blockdevice (mandatory): the block device to partition
   * stripsize (in kB): an optionnal strip size for alignement
   * stripcount: an optionnal number of strip

* do_fs_xfs
  
  Create a xfs file system. If stripsize and stripcount are given, fs alignement hint will be given
  to the mkfs command.

   * part (mandatory): the partion to use
   * logdev: a possible external log device
   * stripsize (in kB): strip size
   * stripcount: the number of strips

* do_mount

  Mount a file system

   * part (mandatory): the partition to mount
   * mount_point (mandatory): where to mount the filesystem
   * fs_type (mandatory): the file system type to mount
   * options: the options to use for the mount

* do_umount

  Try to unmount a file system, don't fail if it's not mounted. Any one of the three arguments needs to be provided
  
   * mount_point : where the filesystem is mounted
   * part: the partition's block device
   * blockdevice: a block device to remove all partitions from
  
* do_mount_xfs

  Mount a xfs file system
   * part (mandatory): the partition to mount
   * mount_point (mandatory): where to mount the filesystem
   * logdev: an optionnal log device
   * noatime: mount with noatime, default to true
   * inode64: use inode64, default to true

* do_fio

  Launch a fio script.

   * label (mandatory): a string to identify the run
   * fio_script (mandatory): the fio script to run
   * fio: the path to the fio command
   * count: the number of fio run

* sched_tune

  Tune the scheduler for the block device

   * blockdevice (mandatory): the block device to tune
   * scheduler: the scheduler name
   * tunes: a mapping of scheduler tune values to set

* clean

  Clean the run directory

   * dir (mandatory): the directory to clean

Variables
=========

The fio scripts are parsed using python's string.Template. The value for a variable is read from the `variable` section in the yaml file.

If a variable is a mapping, it will use the label given to do_fio to find the value to use.

Any variable can be overriden on the command line with -V key=value

For example, by adding the following section to the yaml file:

    variables:
        size:
            A: "1G"
            B: "2G"
            C: "4G"

The do_fio commands with label A, B, C will run the fio script with subtituting the variable ${size} with the respective value "1G", "2G", "4G"
