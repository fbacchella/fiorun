#!env python

import csv
import inspect
import math
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.figure import Figure, SubplotParams
from matplotlib.ticker import FuncFormatter
import numpy
import os
import re
import stat
import string
import subprocess
import sys
import time
import yaml

try:
    import ctypes
    libc = ctypes.CDLL("libc.so.6")
except:
    pass

def check_dev(blockdevice):
    try:
        blockdev = os.stat(blockdevice)
        return stat.S_ISBLK(blockdev.st_mode)
    except:
        return False
    
def get_cciss_info(slot, ld):
    libc.sync()
    check_ld = subprocess.Popen(["/usr/sbin/hpacucli", "ctrl", "slot=%s" % slot, "ld", "%s" % ld, "show"], stdin=None, stdout=subprocess.PIPE)
    output = check_ld.communicate()[0]
    if check_ld.wait() != 0:
        return {}
    values = {}
    for l in re.split("\n", output):
	 entry = re.split(":", l)
         if len(entry) == 2:
             values[entry[0].strip()] = entry[1].strip()
    return values

def wait_cciss_ld(slot, ld):
    while True:
        ld_info = get_cciss_info(slot=slot, ld=ld)
        if not "Parity Initialization Status" in ld_info:
            return True
        if ld_info["Parity Initialization Status"] == "Initialization Completed":
            return True
        if "Parity Initialization Progress" in ld_info:
            print ld_info["Parity Initialization Progress"]
        time.sleep(30)
    return True

completed_re = re.compile("Parity Initialization Status: (.+)")
def do_cciss_ld(slot, ld, stripsize, raid):
    ld_info =  get_cciss_info(slot=slot, ld=ld)
    if 'Disk Name' in ld_info:
        blockdevice = ld_info['Disk Name']
        if check_dev(blockdevice):
            for mount_info in ld_info['Mount Points'].split(','):
                if mount_info.strip() == 'None':
                    continue
                mount_point = mount_info.strip().split(' ')[0]
                smart_unmount(path=mount_point)
            hpacucli = subprocess.Popen(["/usr/sbin/hpacucli", "ctrl", "slot=%s" % slot, "ld", "%s" % ld, "delete", "forced"], stdin=None)	
            if hpacucli.wait() != 0:
                return False
        libc.sync()
    hpacucli = subprocess.Popen(["/usr/sbin/hpacucli", "ctrl", "slot=%s" % slot, "create", "type=ld", "raid=%s" % raid, "drives=all", "ss=%s" % stripsize], stdin=None)
    return hpacucli.wait()

def smart_unmount(path=None, part=None, blockdevice=None):
    if blockdevice:
        if not check_dev(blockdevice):
            return True
        # substitution needed because of cciss/cXdX with HP's Smart Arrays
        old_path = os.getcwdu()
        os.chdir('/sys/block/%s' % blockdevice.replace('/dev/','').replace('/', '!') )
        for d in filter( lambda x: stat.S_ISDIR(os.stat(x).st_mode ) and os.path.exists("%s/dev" % x),
                         os.listdir('.')):
            if smart_unmount(part="/dev/%s" % d.replace('!', '/')) != 0:
                os.chdir(old_path)
                return False
        os.chdir(old_path)
        return 0
    if part:
        proc_mount = open('/proc/mounts', 'r')
        for l in proc_mount.readlines():
            mounted = l.split(" ")
            if mounted[0] == part:
                path = mounted[1]
                break
    if not path:
        return 0
    old_path = os.getcwdu()
    os.chdir(path)
    benchdir = os.stat(".")
    updir = os.stat("..")
    os.chdir(old_path)
    if benchdir.st_dev != updir.st_dev:
        return subprocess.Popen(["umount", path]).wait()
    else:
        return 0

def do_part(blockdevice, stripsize=0, stripcount=0):
    smart_unmount(blockdevice=blockdevice)
    sfdisk_args = ["sfdisk", "-L" ]
    if stripsize != 0 and stripcount != 0:
        while stripsize * 2 > 63:
            stripsize /= 2
            stripcount *= 2
        sfdisk_args.extend(["-uC", "-H", "%s" % stripcount , "-S", "%s" % (stripsize * 2)])
    sfdisk_args.append(blockdevice)
    sfdisk = subprocess.Popen(sfdisk_args, stdin=subprocess.PIPE)
    sfdisk.communicate(input="1,,,\n")
    if sfdisk.wait() == 0:
        libc.sync()
        return subprocess.Popen(["blockdev", "--flushbufs", blockdevice]).wait()
    else:
        return False

def do_xfs(part, logdev=None, stripsize=0, stripcount=0):
    smart_unmount(part=part)
    if not check_dev(part):
        return False
    if logdev and not check_dev(logdev):
        return False
    mkfs_args = ["mkfs.xfs", "-f", "-L", "bench"]
    if logdev:
        mkfs_args.extend(["-l", "logdev=%s" % logdev, "-l", "size=2136997888" ])
    if stripsize !=0 and stripcount != 0:
        mkfs_args.extend(["-d", "su=%s" %(stripsize * 1024), "-d", "sw=%s" % stripcount])
    mkfs_args.append(part)
    return subprocess.Popen(mkfs_args).wait()

def do_mount_xfs(mount_point, part, logdev=None, noatime=True, inode64=True):
    smart_unmount(path=mount_point)
    libc.sync()
    mount_args = ["mount", "-t", "xfs"]
    options = []
    if noatime:
        options.append("noatime")
    if inode64:
        options.append("inode64")
    if logdev:
        options.append("logdev=%s" % logdev)
    if len(options) > 0:
        mount_args.append("-o")
        mount_args.append(",".join(options))
    mount_args.append(part)
    mount_args.append(mount_point)
    return subprocess.Popen(mount_args).wait()
    
def do_fio(label, fio, fio_script, fio_dir, opts = None, count = 1):
    for i in range(count):
        libc.sync()
        drop_caches = open('/proc/sys/vm/drop_caches', 'w')
        drop_caches.write('3')
        drop_caches.close
        try:
            if not stat.S_ISDIR(os.stat(fio_dir).st_mode):
                raise Exception("not fio run dir: %s" % fio_dir)
        except OSError as e:
            if e.errno == 2 and e.filename == fio_dir:
                os.mkdir(fio_dir)
            else:
                raise e
        fio_args = [fio, fio_script, "--minimal"]
        if opts:
            fio_args.extend(opts)
        fio_process = subprocess.Popen(fio_args, stdout=subprocess.PIPE)
        fio_stdout = fio_process.communicate()[0]
        status = fio_process.wait()
        if status != 0:
            raise Exception("fio run failed: %s" % (status))
        fio_stdout = fio_stdout.replace("%", "")
        # a while because this regex will not manage two consecutive string
        while True:
            (fio_stdout, count) = re.subn(r'(^|;)([^;"]*[a-z=][^;"]*)(;|$)',r'\1"\2"\3',fio_stdout)
            if count == 0:
                break
        yield (label, csv.reader(re.split("\n", fio_stdout), delimiter=';', quoting=csv.QUOTE_NONNUMERIC).next())

def run_script(script):
    fio_values = []
    for (f, kwargs)  in script:
        print "step %s(%s)" % (f.__name__, kwargs)
        execute = f(**kwargs)
        print execute.__class__.__name__
        if type(execute) == type(1) and execute != 0:
            raise Exception("%s failed: %s" % (f.__name__, execute))
        elif execute is False:
            raise Exception("%s failed: %s" % (f.__name__, execute))
        elif execute.__class__.__name__ == 'generator':
            for yielded in execute:
                if type(yielded) == type(()) and len(yielded) == 2:
                    row = [ yielded[0] ]
                    row.append(yielded[1][6])
                    row.append(yielded[1][7])
                    row.append(yielded[1][47])
                    row.append(yielded[1][48])
                    row.extend(yielded[1][109:120])
                    fio_values.append(row)
    return fio_values

def run_yaml(script_yaml):
    script = []
    for cmd in script_yaml['run']:
        cmd_name = cmd.keys()[0]
        cmd_args = cmd[cmd_name]
        if cmd_args == None:
            cmd_args = {}
        if cmd_name not in solver:
            print "unknown %s" % cmd_name
        cmd_func = solver[cmd_name]
        kwargs = {}
        for arg_name in inspect.getargspec(cmd_func).args:
            if arg_name in cmd_args:
                kwargs[arg_name] = cmd_args[arg_name]
                del cmd_args[arg_name]
            elif arg_name in script_yaml['default']:
                kwargs[arg_name] = script_yaml['default'][arg_name]
        if len(cmd_args) > 0:
            raise Exception("Unused argument %s for %s" % (cmd_args.keys(), cmd_name))
        script.append((cmd_func, kwargs))

    return run_script(script)

def plot(fio_values, mode="bw", filename=None):
    column_labels = [ "<=2", "4", "10", "20", "50", "100", "250", "500", "750", "1000", "2000", ">=2000" ]
    
    row_labels = []
    ms_values = []
    bw_values_read = []
    bw_values_write = []
    iops_values_read = []
    iops_values_write = []
    for row in fio_values:
        row_labels.append(row[0])
        bw_values_read.append(row[1])
        iops_values_read.append(row[2])
        bw_values_write.append(row[3])
        iops_values_write.append(row[4])
        ms_values.append(row[5:])
        
    waitarray = numpy.array(ms_values).transpose()
    fig = Figure(subplotpars=SubplotParams(right=0.85, left=0.07))
    ax1 = fig.add_subplot(1,1,1)
    # put the major ticks at the middle of each cell, notice "reverse" use of dimension
    ax1.set_xticks(numpy.arange(waitarray.shape[1])+0.5, minor=False)
    ax1.set_xticklabels(row_labels, minor=False)
    ax2 = ax1.twinx()
    
    # draw the heatmap
    ax1.set_yticklabels(column_labels, minor=False)
    ax1.pcolor(waitarray, cmap='bone_r')
    
    # Draw the bw or io/s line
    if mode == "bw":
        to_plot_read = bw_values_read
        to_plot_write = bw_values_write
        ylabel = 'bandwidth'
        radix = 1024
        base = 8
    else:
        to_plot_read = iops_values_read
        to_plot_write = iops_values_write
        ylabel = 'io/s'
        radix = 1000
        base = 10
        
    magnitude_symbols = ["M", "G", "T"]
    # pop start from the end
    magnitude_symbols.reverse()
    min_plot = min(numpy.amin(to_plot_read), numpy.amin(to_plot_write))
    if min_plot != 0:
        min_plot = math.pow(base, math.floor(math.log(min_plot, base)))
    max_plot = max(numpy.amax(to_plot_read), numpy.amax(to_plot_write))
    if max_plot != 0:
        max_plot = math.pow(base, math.ceil(math.log(max_plot, base)))
    
    factor = 1
    symbol = "k"
    max_plot_temp = max_plot
    while max_plot_temp > radix:
        max_plot_temp /= radix
        factor *= radix
        symbol = magnitude_symbols.pop()
    
    if radix == 1024 and symbol:
        symbol += 'i'

    x = numpy.linspace(0.5, len(row_labels) - 0.5, len(row_labels))
    ax2.set_ylabel(ylabel, color='b')
    for tl in ax2.get_yticklabels():
        tl.set_color('b')
    formatter = FuncFormatter(lambda x,y: '%1.0f %s' % (x / factor, symbol))
    ax2.yaxis.set_major_formatter(formatter)
    #ax2.set_ylim(min_plot, max_plot)
    ax2.plot(x, to_plot_read, 'b.-')
    ax2.plot(x, to_plot_write, 'b+-')
    #(y_min, y_max) = ax2.get_ylim()
    #print (y_min, y_max)
    #y_min = math.pow(2 , math.floor(math.log(y_min, 2 )))
    #y_max = math.pow(2 , math.ceil(math.log(y_max, 2)))
    #print (y_min, y_max) 
    #ax2.set_ylim(y_min, y_max)
    #yticks = []
    #for i in range(base):
    #    yticks.append(1.0 * (i/base) * (y_max - y_min) + y_min)
    #ax2.set_yticks(yticks, minor=False)
    
    if filename:
        canvas = FigureCanvasBase(fig)
        canvas.print_figure(filename)
    else:
        # import only when needed, it uses X11
        import matplotlib.pyplot
        matplotlib.pyplot.show()

def save_csv(fio_values, filename):
    with open(filename, 'wb') as csvfile:
        cvsoutput = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        for row in fio_values:
            cvsoutput.writerow(row)

def read_csv(filename):
    values = []
    with open(filename, 'rb') as csvfile:
        csv_input = csv.reader(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        for row in csv_input:
            if row:
                values.append(row)
    plot(values, mode="bw", filename="/tmp/my.png")

def read_yaml(filename):
    yaml_file = open(filename)
    script_yaml = yaml.safe_load(yaml_file)
    yaml_file.close()
    fio_values = run_yaml(script_yaml)

    if('csv' in script_yaml):
        save_csv(fio_values, **script_yaml['csv'])

    plot(fio_values, **script_yaml['plot'])

solver = {}
for function in (do_cciss_ld, wait_cciss_ld, do_part, do_mount_xfs, do_fio, do_xfs):
    solver[function.__name__] = function

[file_use] = sys.argv[1:]
fileName, fileExtension = os.path.splitext(file_use)

if fileExtension == '.csv':
    read_csv(file_use)
else:
    read_yaml(file_use)
