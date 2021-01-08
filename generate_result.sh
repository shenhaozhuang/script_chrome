#!/bin/bash
# Author: shenhaox.zhuang
set -e


echo $1
echo $2
result_path="script_chrome/updateResult/updateExample/"
guest_path="/home/ikvmgt"
host_path="/mnt/stateful_partition"
chroot_path="/home/intel"
bash_result="bash ./upload_result.sh -u shenhaox.zhuang@intel.com -p 123456 -f uploadDetail.zip"
bash_detail="bash ./upload_detail.sh -u shenhaox.zhuang@intel.com -p 123456 -f uploadDetail.zip"
if [ $2 == "guest" ]
then
	apt-get install zip
	cd $1
	cp -p $1/result.csv $guest_path/$result_path
	zip -r $guest_path/$result_path/detail.zip *
	cd $guest_path/$result_path
	zip -r ../uploadDetail.zip *
	cd ..
	$bash_result
	$bash_detail
elif [ $2 == "host" -o $2 == "android" ]
then
	cd $1
	cp -p $1/result.csv $host_path/$result_path
       	zip -r $host_path/$result_path/detail.zip *
	cd $host_path/$result_path
	zip -r ../uploadDetail.zip *
	cd ..
	$bash_result
	$bash_detail
elif [ $2 == "chroot" ]
then
	apt-get install zip
	cd $1
	cp -p $1/result.csv $chroot_path/$result_path
	zip -r $chroot_path/$result_path/detail.zip *
	cd $chroot_path/$result_path
	zip -r ../uploadDetail.zip *
	cd ..
	$bash_result
	$bash_detail
else
	cd $1
	cp -p $1/result.csv $chroot_path/$result_path
	zip -r $chroot_path/$result_path/detail.zip *
	cd $chroot_path/$result_path/
	zip -r ../uploadDetail.zip *
	cd ..
	$bash_result
	$bash_result
fi

all(){
echo $1
cd $1
cp -p $1/result.csv /home/ikvmgt/script_chrome/updateResult/updateExample/
zip -r /home/ikvmgt/script_chrome/updateResult/updateExample/detail.zip *
cd /home/ikvmgt/script_chrome/updateResult/updateExample/
zip -r ../uploadDetail.zip *
cd ..
bash ./upload_result.sh -u shenhaox.zhuang@intel.com -p 123456 -f uploadDetail.zip
bash ./upload_detail.sh -u shenhaox.zhuang@intel.com -p 123456 -f uploadDetail.zip
}

