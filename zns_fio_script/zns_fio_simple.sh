sudo fio --ioengine=libaio --direct=1 --filename=/dev/nvme1n1 --rw=write --bs=192k --group_reporting --zonemode=zbd --name=seqwrite --offset_increment=128M --size=128M --numjobs=8 --job_max_open_zones=1
#sudo fio --ioengine=libaio --direct=1 --filename=/dev/nvme1n1 --rw=randread --bs=4k --group_reporting --zonemode=zbd --name=ranread --numjobs=4 --iodepth=8 --runtime=60 --size=1G
sudo fio --ioengine=libaio --direct=1 --filename=/dev/nvme1n1 --rw=randread --bs=4k --group_reporting --name=randread --numjobs=16 --iodepth=16 --runtime=10 --offset=10M --size=64M --time_based
