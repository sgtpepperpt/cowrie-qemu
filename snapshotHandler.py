import shutil
import getpass
import subprocess
import random
import os

snapshotXML = '''
<domainsnapshot>
    <memory snapshot='no'/>
    <disks>
        <disk name='/var/lib/libvirt/images/ubuntu18.04.qcow2'>
            <driver type='qcow2'/>
            <source file='/var/lib/libvirt/images/ubuntu18.04snapshot.qcow2'/>
        </disk>
    </disks>
</domainsnapshot>
'''


def create_disk_snapshot(source_img, destination_img):
    # s = domain.listAllSnapshots()
    # ret = domain.snapshotCreateXML(snapshotXML, libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY)

    shutil.chown(source_img, getpass.getuser())
    out = subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-b', source_img, destination_img], capture_output=True)
    return out.returncode == 0


def generate_image_path(base_path, image_tag):
    while True:
        seed = random.getrandbits(32)
        path = base_path + 'snapshot-{0}-{1}-qcow2.img'.format(image_tag, seed)
        if not os.path.isfile(path):
            return path