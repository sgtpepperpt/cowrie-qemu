import shutil
import getpass
import subprocess


def create_disk_snapshot(source_img, destination_img):
    # snapshot_xml = util.read_file('config_files/default_snapshot.xml')
    # s = domain.listAllSnapshots()
    # ret = domain.snapshotCreateXML(snapshot_xml, libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY)

    shutil.chown(source_img, getpass.getuser())
    out = subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-b', source_img, destination_img], capture_output=True)
    return out.returncode == 0
