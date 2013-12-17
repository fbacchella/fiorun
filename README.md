fiorun
======

A python script to launch many fio bench.

It can be used to create a logical drive, create a new partition or reformat the partition.

Actually, only HP's smart array logical drive are supported, help is welcome.

It only runs on linux.

It take a yaml file as an argument that describes the step to execute.

After the execution a image and a csv is produced with values.

The image shows an heat map with response time and plot the bandwith or io/s.

The sections for the yaml file are :

* defaults, to describe common values
  
  each command will look in the defaults for the missing arguments. Every default value can be change on the command line with -D key=value

* variables, some variables used in the fio script
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
      - do_xfs:
      - do_mount_xfs:
      - do_fio:
          label: "A"
    # unaligned and log device
      - do_xfs:
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

  apply a modification on a Smart Array controler

   * object (mandatory): either ctrl or ld, will apply the modification on the controler or the logicial drive
   * command (mandatory): the modify command to execute
   * slot: the slot to identify the controler
   * ld: the logical drive

* do_cciss_ld

  create a logical drive on a Smart Array controller

* wait_cciss_ld
* do_part
* do_mount_xfs
* do_fio
* do_xfs

Variables
=========

The fio scripts are parsed using python's string.Template. The value for a variable is read from the `variable` section in the yaml file.

If a variable is a mapping, it will use the label given to do_fio to find the value to use.

Any variable can be overriden on the command line with -V key=value
