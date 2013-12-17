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
default, to describe common values
plot, to describe the output image
csv, to describe the output csv
run, the steps to execute.

A simple yaml look likes :

default:
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
      label: "simple xfs"
# unaligned and log device
  - do_xfs:
      logdev: "/dev/sdc"
  - do_mount_xfs:
      logdev: "/dev/cciss/c0d2"
  - do_fio:
      label: "with logdevice"

Installation
============

It needs matplotlib and PyYAML.

So to build an python virtual env with latest dependencies version, on a redhat, one can run :
yum-builddep python-matplotlib numpy PyYAML
yum install python-virtualenv
cd /opt/bench
virtualenv pybench
pybench/bin/pip install matplotlib
pybench/bin/pip install PyYAML