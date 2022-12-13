.PHONY: build
build:
	build/build_hwmd.sh

# faster build for debugging/development purposes
#   on pedro's laptop the difference is around 14s vs 1min20s
build_dev:
	DEBUG=1 build/build_hwmd.sh

# force build of bullseye
build_bullseye:
	VERSION_CODENAME='bullseye' build/build_hwmd.sh

# remove all files generated by build iso
build_clean:
	rm -rf build/iso/*

install_HWMD_dependencies:
	# Add bullseye backports to install lshw=02.19* utility
	echo "deb http://deb.debian.org/debian bullseye-backports main contrib" | sudo tee /etc/apt/sources.list.d/backports.list
	sudo apt update
	# Install WB debian requirements
	cat requirements.debian.txt | sudo xargs apt install -y
	# Install WB python requirements
	sudo pip3 install -r requirements.txt

run:
	DISABLE_HWINFO=1 python3 hwmetadata_core.py

test:
	DISABLE_HWINFO=1 python3 -m unittest tests/test.py -v

boot_iso:
	sudo qemu-system-x86_64 \
		-enable-kvm -m 2G -vga qxl -netdev user,id=wan -device virtio-net,netdev=wan,id=nic1 \
		-drive format=raw,file=build/iso/USODY_debug.iso,cache=none,if=virtio

# src https://www.ubuntubuzz.com/2021/04/how-to-boot-uefi-on-qemu.html
#   needs `sudo apt-get install ovmf`
boot_iso_uefi:
	sudo qemu-system-x86_64 \
		-bios /usr/share/ovmf/OVMF.fd \
		-enable-kvm -m 2G -vga qxl -netdev user,id=wan -device virtio-net,netdev=wan,id=nic1 \
		-drive format=raw,file=build/iso/USODY_debug.iso,cache=none,if=virtio

boot_iso_uefi_secureboot:
	# For ovmf 2020.08-1, the change of boot order is usually necessary because the UEFI shell has the highest boot priority in OVMF_VARS*.ms.fd.
	sudo cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd /tmp/efivars_4M.fd
	# src https://wiki.debian.org/SecureBoot/VirtualMachine
	sudo qemu-system-x86_64 \
		-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on \
		-drive if=pflash,format=raw,unit=0,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd,readonly=on \
		-drive if=pflash,format=raw,unit=1,file=/tmp/efivars_4M.fd \
		-enable-kvm -m 2G -vga qxl -netdev user,id=wan -device virtio-net,netdev=wan,id=nic1 \
		-drive file=build/iso/USODY_debug.iso,cache=none,if=virtio,format=raw,index=0,media=disk \
		-boot menu=on

#remove snapshots folder
snapshots_clean:
	rm -rf snapshots/