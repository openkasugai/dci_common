#!/bin/bash

case $1 in
  "d1-f01-k8s-master01 ")       ★引数として指定するVM名＝VMNAME
    VMNAME=d1-f01-k8s-master01  ★VM名
    VCPUS=8                     ★VMに付与するCPU数
    RAMSIZE=16                  ★VMに付与するメモリサイズ(Unit:GB)
    DISKSIZE=100                ★VMに付与するディスクサイズ(Unit:GB)
    IPADDR=172.28.193.10        ★VMのマネージャNWのIPアドレス
    ;;
  "d1-f01-k8s-master02 ")       ★複数作成する場合は、１つめと同様に編集して追加する
    VMNAME=d1-f01-k8s-master02  ★
    VCPUS=4                     ★
    RAMSIZE=16                  ★
    DISKSIZE=100                ★
    IPADDR=172.28.193.11        ★
esac

# Directory where image files will be stored
IMAGE_DIR=/var/lib/libvirt/images
# VM image file name
IMAGE_FILE=${VMNAME}.qcow2
# Base image file name (must exists before running the script)
BASE_FILE=rhel-9.6-x86_64-kvm.qcow2

CIDATA_PATH=$IMAGE_DIR/cidata-${VMNAME}.iso
#CIDATA_PATH=$PWD/cidata-${VMNAME}.iso
IMAGE_PATH=$IMAGE_DIR/$IMAGE_FILE
BASE_PATH=$IMAGE_DIR/$BASE_FILE

echo "VMNAME ........ $VMNAME"
echo "VCPUS ......... $VCPUS"
echo "RAMSIZE ....... $RAMSIZE G"
echo "DISKSIZE ...... $DISKSIZE G"
echo "IPADDR ........ $IPADDR"
echo "CIDATA_PATH ... $CIDATA_PATH"
echo "IMAGE_PATH .... $IMAGE_PATH"
echo "BASE_PATH ..... $BASE_PATH"
echo
read -p "Is this OK? ('y' to proceed) " ANS
if [ "$ANS" != "y" -a "$ANS" != "Y" ]; then
  echo "Aborted"
  exit 1
fi

# Go to the image dir
pushd $IMAGE_DIR

# Check if the base image exists
if sudo [ ! -r "$BASE_FILE" ]; then
  echo "error: base image file $BASE_PATH not found."
  exit 1
fi

# Check if the VM image already exists
# if not, create the new one
if sudo [ ! -f "$IMAGE_FILE" ]; then
  echo "info: image file $IMAGE_PATH not found. creating new image"
  sudo qemu-img create -f qcow2 -F qcow2 -b "$BASE_PATH" "$IMAGE_FILE" ${DISKSIZE}G
  if [ $? -ne 0 ]; then
    echo "error: failed to create image"
    exit 1
  fi
fi

# Dump the image info
sudo qemu-img info "$IMAGE_FILE"

popd

# Check if the cloud-init data file exists
# if not, generate it
if [ ! -r $CIDATA_PATH ]; then
  mkdir -p $VMNAME
  cd $VMNAME

  cat > user-data <<-EOS
#cloud-config
password: <Password>            ★ログインパスワード(ログインユーザはデフォルトで cloud-user)
chpasswd: {expire: False}
ssh_pwauth: True
timezone: "Asia/Tokyo"
EOS

  cat > network-config << EOS
network:
  version: 1
  config:
    - type: physical
      name: eth1
      subnets:
        - type: static
          address: $IPADDR/24
          gateway: 172.28.193.251★デフォルトゲートウェイのIPアドレス
EOS

  cat > meta-data <<-EOS
instance-id: $VMNAME
local-hostname: $VMNAME
EOS

  genisoimage -output "$CIDATA_PATH" -volid cidata -joliet -rock user-data meta-data network-config
  cd ..
fi

sudo virt-install \
  --name $VMNAME \
  --ram $(($RAMSIZE * 1024)) \
  --vcpus $VCPUS \
  --os-variant rhel9.0 \
  --arch x86_64 \
  --virt-type kvm \
  --boot hd \
  --disk $IMAGE_PATH,device=disk,bus=virtio,format=qcow2 \
  --disk $CIDATA_PATH,device=cdrom \
  --network network:default \
  --network bridge:br0 \
  --graphics none \
  --import
