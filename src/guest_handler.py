# Copyright (c) 2019 Guilherme Borges <guilhermerosasborges@gmail.com>
# See the COPYRIGHT file for more information

import sys
import libvirt

import snapshot_handler
import util


class QemuGuestError(Exception):
    pass


def create_guest(connection, mac_address, unique_id):
    version_tag = 'ubuntu18.04'

    # create a disk snapshot to be used by the guest
    source_img = '/home/gb/Repositories/qemu/ubuntu18.04.qcow2.bak'
    disk_img = '/home/gb/Repositories/qemu/snapshot-{0}-{1}-qcow2.img'.format(version_tag, unique_id)

    if not snapshot_handler.create_disk_snapshot(source_img, disk_img):
        print('There was a problem creating the disk snapshot.', file=sys.stderr)
        raise QemuGuestError()

    guest_xml = util.read_file('../config_files/default_guest.xml')
    guest_config = guest_xml.format(guest_name='cowrie-ubuntu18.04-' + unique_id,
                                    disk_image=disk_img,
                                    mac_address=mac_address,
                                    network_name='cowrie')

    try:
        dom = connection.createXML(guest_config, 0)
        if dom is None:
            print('Failed to create a domain from an XML definition.', file=sys.stderr)
            exit(1)

        print('Guest ' + dom.name() + ' has booted', file=sys.stderr)
        return dom, disk_img
    except libvirt.libvirtError as e:
        print('Error booting guest: {0}'.format(e))
        raise e
