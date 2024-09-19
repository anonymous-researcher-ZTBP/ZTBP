# ZTBP ( ZNS Trace Bypass Platform )

ZTBP is an extension of the NVMeVirt project, focusing on enhancing ZNS SSD performance through eBPF-driven analysis and intelligent data clustering.
If you want to find the basic installation please visit the (https://github.com/snu-csl/nvmevirt)
## Overview

ZTBP leverages the zone-based structure of ZNS SSDs to optimize read-intensive operations. It uses eBPF technology and machine learning algorithms to dynamically identify and optimize read-intensive zones without kernel modifications.

Key features:
- Real-time NVMe IO tracing
- Zone-specific cache optimization
- Novel SLC migration technique for high read-intensity zones

## Installation

For basic installation instructions, please refer to the [NVMeVirt GitHub repository](https://github.com/nvmevirt/nvmevirt).

After following the NVMeVirt installation steps, proceed with the following ZTBP-specific setup:

1. Clone this repository:
   ```
   git clone https://github.com/anoymous-researcher-ZTBP/ZTBP.git
   cd ZTBP
   ```

2. Install additional dependencies (if any):
   ```
   same as nvmevirt
   ```

3. Install for ebpf and nvmeutil 
   '''
   install BCC project
   install nvme-utils
   install python3 upper 3.7
   '''

## Usage

1. Provide steps to run ZTBP
   '''
   sudo ./init_nvmev.sh
   sudo ebpf_script/biosnoop_nvme.py
   '''   
2. benchmark test for fio
   sudo fio zns_fio_script/zns_fio_simple.sh
   sudo fio zns_fio_script/zns_fio_40.fio
   sudo fio zns_fio_script/zns_fio_60.fio
   sudo fio zns_fio_script/zns_fio_80.fio

## ZTBP-Specific Features

### eBPF-Driven I/O Analysis

ZTBP utilizes eBPF (extended Berkeley Packet Filter) technology to perform real-time analysis of NVMe I/O operations:

- **Dynamic Tracing**: Captures and analyzes NVMe commands in real-time without kernel modifications.
- **Low Overhead**: Minimizes performance impact while providing detailed insights into I/O patterns.
- **Customizable Filters**: Allows users to focus on specific types of I/O operations or zones.

### DB Clustering for Access Pattern Recognition

The DB clustering feature in ZTBP helps in recognizing and optimizing for complex I/O access patterns:

- **Workload Classification**: Groups similar I/O patterns to identify common access behaviors.
- **Adaptive Optimization**: Tailors caching and prefetching strategies based on identified clusters.
- **Performance Tuning**: Provides insights for fine-tuning ZNS SSD configurations.

## Contributing

Contributions to ZTBP are welcome. Please feel free to submit pull requests or open issues to discuss proposed changes or report bugs.

## License

ZTBP is based on NVMeVirt and follows its licensing terms:

1. The main project is offered under the terms of the GNU General Public License version 2 (GPLv2) as published by the Free Software Foundation. For more information about this license, please visit [GNU GPL v2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).

2. The priority queue implementation in the `pqueue/` directory is offered under the terms of the BSD 2-clause license (GPL-compatible). 
   Copyright (c) 2014, Volkan Yazıcı <volkan.yazici@gmail.com>. All rights reserved.

Any modifications or extensions made in ZTBP are also released under the GNU General Public License version 2, to maintain compatibility with the original project.

For full license texts, please refer to the [LICENSE](LICENSE) and [pqueue/LICENSE](pqueue/LICENSE) files in this repository.

## Contact

For any questions or support regarding ZTBP, please contact "".

## Acknowledgments

- This project is based on [NVMeVirt](https://github.com/nvmevirt/nvmevirt).



