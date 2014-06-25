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

In samples, one can find a full configuration, that compare performance for different RAID level on a HP Smart Array.

It builds 3 logicaldrive, with a different RAID level for each one and ran an 8k block, random mix of 70 % read /30% write.

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

* do_delete_all_cciss

   Loop to delete the specified array. Usefull if you want to delete a bunch of arrays. Only the first array must be
   given, all the next one will be destroy. Beware, it stops only where is nothing left to do. So if the last array needs
   to be kept, don't use it.
    
   * hpacucli, the path to the hpacucli command
   * slot, the slot where to look for the array
   * array, the array to destroy
   
   
* modify_cciss

  apply a modification on a HP's SmartArray controler

   * object (mandatory): either ctrl or ld, will apply the modification on the controller or the logical drive
   * command (mandatory): the modify command to execute
   * slot: the slot to identify the controller
   * ld: the logical drive

* do_cciss_create_ld

  create a logical drive on a HP's SmartArray. If ld or array is given, it's destroyed before the creation.

   * slot (mandatory): the slot to identify the controller
   * ld (mandatory): the logical drive
   * stripsize: a possible stripsize to use
   * size: define a ld size, in megabyte

* do_cciss_add_ld

  Add a ld to an array.

   * slot (mandatory): the slot to identify the controller
   * ld (mandatory): the logical drive
   * stripsize: a possible stripsize to use
   * size: define a ld size, in megabyte

* wait_cciss_ld

  Wait for HP's SmartArray logical drive to be ready after a RAID creation. Either a ld or a array must be given.

   * slot (mandatory): the slot to identify the controller
   * ld : the logical drive what was created
   * array: the array where the ld was created, wait for all the logical drives in the array.

* do_part

  Create a partition on a block device. If stripsize and stripcount are given, cylinder size
  will be stripsize * stripcount.

   * blockdevice (mandatory): the block device to partition
   * stripsize (in kB): an optionnal strip size for alignment
   * stripcount: an optional number of strip

* do_fs_xfs
  
  Create a xfs file system. If stripsize and stripcount are given, fs alignment hint will be given
  to the mkfs command.

   * part (mandatory): the partition to use
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
   * logdev: an optional log device
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

* mkpath

  Create a directory, make parent directories as needed.

   * dir (mandatory): the directory to create

* cgroup_prepare

  Prepare a cgroup submodule for cgroups bench, it will be called /cgroup/blkio/fiorun

* do_cgroup_fio
  
  Run fio in a dedicated cgroup, with a given set of tunables values.
  
  * mount_point (mandatory): the mount point for the bench run, will be used to find the block device to apply the cgroup
  * tunables (mandatory): a set of cgroup tunable
  * label (mandatory): a string to identify the run
  * fio_script (mandatory): the fio script to run
  * fio: the path to the fio command
  * count: the number of fio run

Plot
====

The plot section controls how the graph output.

It takes three parameters:

* filename: the filename for the generated file
* title: the graph title
* mode: either "bw" or "iops", does the graph output the bandwidth or the io/s

csv
====

If provided, the values will be saved as a csv file, for latter reuse. It take one argument, the csv file name

It takes three parameters:

* filename: the filename for the generated file
* title: the graph title
* mode: either "bw" or "iops", does the graph output the bandwidth or the io/s

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

Variables
=========

fiorun can run many yaml scripts. If a template is provided in command line, default values for each sections will be used.
Then each yaml script can be reduced to a bare minimum.

Sections 'defaults', 'variables', 'plot', 'csv' are merged. Section 'run' is totally replaced.
