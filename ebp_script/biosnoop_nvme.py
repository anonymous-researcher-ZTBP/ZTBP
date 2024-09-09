#!/usr/bin/env python
# @lint-avoid-python-3-compatibility-imports
#
# biosnoop  Trace block device I/O and print details including issuing PID.
#           For Linux, uses BCC, eBPF.
#
# This uses in-kernel eBPF maps to cache process details (PID and comm) by I/O
# request, as well as a starting timestamp for calculating I/O latency.
#
# Copyright (c) 2015 Brendan Gregg.
# Licensed under the Apache License, Version 2.0 (the "License")
#
# 16-Sep-2015   Brendan Gregg   Created this.
# 11-Feb-2016   Allan McAleavy  updated for BPF_PERF_OUTPUT
# 21-Jun-2022   Rocky Xing      Added disk filter support.
# 13-Oct-2022   Rocky Xing      Added support for displaying block I/O pattern.
# 01-Aug-2023   Jerome Marchand Added support for block tracepoints

from __future__ import print_function
from bcc import BPF
import argparse
import os

#DB Scanning
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import numpy as np

import subprocess

# arguments
examples = """examples:
    ./biosnoop           # trace all block I/O
    ./biosnoop -Q        # include OS queued time
    ./biosnoop -d sdc    # trace sdc only
    ./biosnoop -P        # display block I/O pattern
"""
parser = argparse.ArgumentParser(
    description="Trace block I/O",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)
parser.add_argument("-Q", "--queue", action="store_true",
    help="include OS queued time")
parser.add_argument("-d", "--disk", type=str,
    help="trace this disk only")
parser.add_argument("-P", "--pattern", action="store_true",
    help="display block I/O pattern (sequential or random)")
parser.add_argument("--ebpf", action="store_true",
    help=argparse.SUPPRESS)
args = parser.parse_args()
debug = 0

global_tracing_list = list()
MAX_CLUSTER_CNT = 10000

# define BPF program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/blk-mq.h>
"""

# define NVMe tracing
bpf_text += """
#include <linux/nvme.h>
#include <linux/tracepoint.h>
#include <linux/trace_seq.h>
#include <linux/blkdev.h>
#include <asm/unaligned.h>

"""

if args.pattern:
    bpf_text += "#define INCLUDE_PATTERN\n"

bpf_text += """

struct data_nvme_t {
    char disk[32];
    int ctrl_id;
    int qid;
    u8 opcode;
    u8 flags;
    u8 fctype;
    u16 cid;
    u32 nsid;
//    bool metadata;
    u8 cdw10[24];
    u64 slba;
    u16 length;
    u16 control;
    u32 dsmgmt;
    u32 reftag;
};

/*
 * Common request structure for NVMe passthrough.  All drivers must have
 * this structure as the first member of their request-private data.
 */
struct nvme_request_cp {
    struct nvme_command *cmd;
    union nvme_result   result;
    u8          genctr;
    u8          retries;
    u8          flags;
    u16         status;
    struct nvme_ctrl    *ctrl;
};

#ifdef INCLUDE_PATTERN
BPF_HASH(last_sectors, struct sector_key_t, u64);
#endif

//BPF_HASH(start, struct hash_key, struct start_req_t);
//BPF_HASH(infobyreq, struct hash_key, struct val_t);
BPF_PERF_OUTPUT(events);

#if 0
int trace_nvme_feedback(struct pt_regs *ctx,struct request *req)
{
    struct nvme_request_cp *request = blk_mq_rq_to_pdu(req);
    struct data_nvme_t data={};

    data.opcode = 12;    

    data.cid = le32_to_cpu(request->result.u32);
    data.nsid = request->result.u16;
    data.length = request->result.u64;

    events.perf_submit(ctx,&data,sizeof(data));
    return 0;
}
#endif
int trace_nvme_completion(struct pt_regs *ctx,int temp, struct request *req)
{
    struct nvme_request_cp *request = blk_mq_rq_to_pdu(req);
    struct nvme_command *cmd = request->cmd;

    struct data_nvme_t data={};  

    //data.ctrl_id = nvme_req(req)->ctrl->instance;
    if (!req->q->queuedata)
        data.qid = 0;
    else
        data.qid = req->mq_hctx->queue_num + 1;    
    
    data.opcode = req->cmd_flags & REQ_OP_MASK;
    data.flags = request->cmd->common.flags;


    data.cid = request->cmd->common.command_id;

    data.nsid = request->cmd->common.nsid;
    data.fctype = cmd->fabrics.fctype;
    const char *disk_name = req->q->disk->disk_name;
    
    if (req->q->disk){
         bpf_probe_read_kernel(&data.disk, sizeof(data.disk), disk_name);
    }
    bpf_probe_read_kernel(&data.cdw10,sizeof(data.cdw10),&cmd->common.cdw10);

    data.slba = get_unaligned_le64(data.cdw10);
                
    data.length = get_unaligned_le16(data.cdw10+8) + 1;
    data.control = get_unaligned_le16(data.cdw10+10);
    data.dsmgmt = get_unaligned_le32(data.cdw10+12);
    data.reftag = get_unaligned_le32(data.cdw10+16);   

    events.perf_submit(ctx, &data, sizeof(data));

#if 0    
    valp = infobyreq.lookup(&key);
    if (valp == 0) {
        data.name[0] = '?';
        data.name[1] = 0;
    } else {
        if (##QUEUE##) {
            data.qdelta = startp->ts - valp->ts;
        }
        data.pid = valp->pid;
        data.sector = key.sector;
        data.dev = key.dev;
        bpf_probe_read_kernel(&data.name, sizeof(data.name), valp->name);
    }
    data.rwflag = key.rwflag;

    events.perf_submit(ctx, &data, sizeof(data));
    start.delete(&key);
    infobyreq.delete(&key);
#endif
    return 0;    
}

"""

if args.disk is not None:
    disk_path = os.path.join('/dev', args.disk)
    if not os.path.exists(disk_path):
        print("no such disk '%s'" % args.disk)
        exit(1)

    stat_info = os.stat(disk_path)
    dev = os.major(stat_info.st_rdev) << 20 | os.minor(stat_info.st_rdev)

    disk_filter_str = """
    if(key.dev != %s) {
        return 0;
    }
    """ % (dev)

    bpf_text = bpf_text.replace('DISK_FILTER', disk_filter_str)
else:
    bpf_text = bpf_text.replace('DISK_FILTER', '')

if debug or args.ebpf:
    print(bpf_text)
    if args.ebpf:
        exit()

# initialize BPF
b = BPF(text=bpf_text)

if BPF.get_kprobe_functions(b'nvme_setup_cmd'):
    b.attach_kprobe(event="nvme_setup_cmd", fn_name="trace_nvme_completion")
#if BPF.get_kprobe_functions(b'nvme_complete_rq'):
#    b.attach_kprobe(event="nvme_complete_rq", fn_name="trace_nvme_feedback")
# header
print("[In-Kernel Trace] NVMe IO CLUSTER Operations")

# cache disk major,minor -> diskname
diskstats = "/proc/diskstats"
disklookup = {}
with open(diskstats) as stats:
    for line in stats:
        a = line.split()
        disklookup[a[0] + "," + a[1]] = a[2]


# process event
def print_event(cpu, data, size):
    event = b["events"].event(data)
    
    addr_gb = '('+ str(format(float(event.slba)*512/1024/1024/1024,".2f"))+'Gbytes)'
    blk_length = str( (event.length)*512/1024)+'kb'
    print(
          event.disk,
          event.ctrl_id,
          event.qid, 
          event.opcode, 
          event.flags,
          event.fctype,
          event.cid,
          event.nsid,
          event.slba,
          addr_gb,
          blk_length,
          event.control,
          event.dsmgmt,
          event.reftag,
    )
def on_clustering_operation(y_range_dict=dict(),x_range_dict=dict(),raw_data=list()):

    for cmd_idx in y_range_dict.keys():
        y_latency_group = y_range_dict[cmd_idx]
        x_range_group = x_range_dict[cmd_idx]

        temp_list = list()
        for idx in range(0, len(x_range_group)):
            temp_list.append([x_range_group[idx], y_latency_group[idx]])
        scaler = StandardScaler()
        scale_data = scaler.fit_transform(temp_list)

        try:
            val_eps = float(txt.split(',')[0].split('eps:')[1])
            val_min_samples = int(txt.split(',')[1].split('min_samples:')[1])
        except:
            val_eps = 0.05
            val_min_samples = 20

        dbscan = DBSCAN(eps=val_eps, min_samples=val_min_samples)
        clusters = dbscan.fit_predict(scale_data)

    clusters_group = dict()
    zone_freq_info = dict()

    for i in range(scale_data.shape[0]):
        raw_data[i]['cluster'] = clusters[i]
        #second filter
        if clusters[i] !=-1:
            try:
                zone_freq_info[raw_data[i]['zone_id']] += 1
            except:
                zone_freq_info[raw_data[i]['zone_id']] = 1
                
        if not  clusters[i] in clusters_group:
            clusters_group[clusters[i]] = {'x':[scale_data[i, 0]],'y':[scale_data[i, 1]]}

        else:
            clusters_group[clusters[i]]['x'].append(scale_data[i, 0])
            clusters_group[clusters[i]]['y'].append(scale_data[i, 1])

    threshould_intensive_zone = scale_data.shape[0] / 100
    return sorted([(k, v) for k, v in zone_freq_info.items() if v > threshould_intensive_zone ], key=lambda x: x[1], reverse=True)
#    return np.unique(clusters)
'''     
        color_list = ['r', 'g', 'b', 'c', 'm', 'y', 'w', 'k']
        cmap = {label: np.random.choice(color_list) for label in set(clusters)}
        clusters_group = dict()           
        for i in range(scale_data.shape[0]):
            self.raw_item[i]['cluster'] = clusters[i]
            if not clusters[i] in clusters_group:
                clusters_group[clusters[i]] = {'x': [scale_data[i, 0]], 'y': [scale_data[i, 1]]}

            else:
                clusters_group[clusters[i]]['x'].append(scale_data[i, 0])
                clusters_group[clusters[i]]['y'].append(scale_data[i, 1])

        for group_idx in clusters_group.keys():
            scatter = pg.ScatterPlotItem(symbol=cmd_symbol, name=cmd_name, x=clusters_group[group_idx]['x'],
                                         y=clusters_group[group_idx]['y'], brush=brush)
                                         
'''

def on_length_addr_operation(raw_data=list()):

    y_range_dict = dict()
    x_range_dict = dict()
    for item in raw_data:
        cmd = item['opcode']
        addr = item['slba']
        len = item['blk_length']
        if item['opcode'] not in y_range_dict:
            y_range_dict[cmd] = list()
            y_range_dict[cmd].append(addr)

            x_range_dict[cmd] = list()
            x_range_dict[cmd].append(len)
        else:
            y_range_dict[cmd].append(addr)
            x_range_dict[cmd].append(x_range_dict[cmd][-1]+len)

    return on_clustering_operation(y_range_dict,x_range_dict,raw_data)

def on_tracing_buffer(cpu,data, size):
    event = b["events"].event(data)
    addr_gb = '(' + str(format(float(event.slba) * 512 / 1024 / 1024 / 1024, ".2f")) + 'Gbytes)'
    blk_length = str((event.length) * 512 / 1024) + 'kb'
    log = dict()
    zone_size = 32

    log['disk'] = event.disk
    log['ctrl_id'] =event.ctrl_id
    log['qid'] =event.qid
    log['opcode'] =event.opcode
    log['flags'] =event.flags
    log['fctype'] =event.fctype
    log['cid'] =event.cid
    log['nsid'] =event.nsid
    log['slba'] =event.slba
    log['blk_length'] =event.length
    log['zone_id'] = int(event.slba/2/1024/zone_size)
#    print(log)
    global_tracing_list.append(log)

    if len(global_tracing_list) > 10000:
        try:
            print("clustering operation enable")
            cluster_list = on_length_addr_operation(global_tracing_list)
            print(cluster_list)
            cmd_opt = ""
            cmd_opt +="sudo nvme admin-passthru /dev/nvme1n1 --opcode=0x99 "
            cmd_opt +="--cdw10=99 "
            cmd_opt +="--cdw11="+str(cluster_list[0][0])+" "
            cmd_opt +="--cdw12="+str(cluster_list[1][0])+" "
            cmd_opt +="--cdw13="+str(cluster_list[2][0])+" "
            cmd_opt +="--cdw14="+str(cluster_list[3][0])+" "
            cmd_opt +="--cdw15="+str(cluster_list[4][0])
            print(cmd_opt)
            print(subprocess.run(cmd_opt,shell=True,stdout=subprocess.PIPE,text=True));
            
    #       print(subprocess.run("sudo nvme /dev/nvme1n1 --cdw10=10 --cdw11=50 --cdw12=3",shell=True,stdout=subprocess.PIPE,text=True))
            global_tracing_list.clear()
        except:
            print("something wrog")
            global_tracing_list.clear()

# loop with callback to print_event
b["events"].open_perf_buffer(on_tracing_buffer, page_cnt=64)
while 1:
    try:
        b.perf_buffer_poll()
    except KeyboardInterrupt:
        exit()
