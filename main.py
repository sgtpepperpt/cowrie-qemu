import os
import sys
import libvirt
from time import sleep

import guest_handler
import network_handler
import snapshot_handler
import util


def tests(dom, network):
    type = dom.info()
    print('The name of the domain is "' + str(type) + '".')

    # print(dom.XMLDesc())

    flag = dom.hasCurrentSnapshot()
    print('The value of the current snapshot flag is ' + str(flag))


def main():
    # open connection to libvirt
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)

    # create a NAT for the guests
    network = network_handler.create_network(conn)

    # create a disk snapshot to be used by the guest
    source_img = '/home/gb/Repositories/qemu/ubuntu18.04.qcow2'
    destination_img = snapshot_handler.generate_image_path('/home/gb/Repositories/qemu/', 'ubuntu18.04')
    if not snapshot_handler.create_disk_snapshot(source_img, destination_img):
        print('There was a problem creating the disk snapshot.', file=sys.stderr)
        exit(1)

    # create a single guest
    dom = guest_handler.create_guest(conn, destination_img)
    if dom is None:
        print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
        exit(1)

    # use guest
    tests(dom, network)

    count = 0

    # wait until network is up in guest
    while not util.nmap_ssh():
        sleep(1)
        print('{0} Guest not ready'.format(count))
        count += 1

    # now backend is ready for connections
    print('Guest ready for SSH connections!')

    # destroy created guest
    print('Destroying guest!')
    dom.destroy()

    # destroy its disk snapshot
    os.remove(destination_img)

    # destroy transient network
    network.destroy()

    # close libvirt connection
    conn.close()


main()
