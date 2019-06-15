import sys
import libvirt
import util
from time import sleep

import guest_handler
import network_handler
import snapshot_handler


class QemuError(Exception):
    pass


class QemuService:
    def __init__(self):
        # open connection to libvirt
        self.conn = libvirt.open('qemu:///system')
        if self.conn is None:
            print('Failed to open connection to qemu:///system', file=sys.stderr)
            raise QemuError()

        # create a NAT for the guests
        self.network = network_handler.create_network(self.conn)

        print('Connection to Qemu established')

        # data structs
        self.guests = []

    def __del__(self):
        self.network.destroy()  # destroy transient network
        self.conn.close()  # close libvirt connection

        print('Connection to Qemu closed successfully')

    def create_guest(self):
        # create a disk snapshot to be used by the guest
        source_img = '/home/gb/Repositories/qemu/ubuntu18.04.qcow2'
        destination_img = snapshot_handler.generate_image_path('/home/gb/Repositories/qemu/', 'ubuntu18.04')

        if not snapshot_handler.create_disk_snapshot(source_img, destination_img):
            print('There was a problem creating the disk snapshot.', file=sys.stderr)
            return None

        # create a single guest
        dom = guest_handler.create_guest(self.conn, destination_img)
        if dom is None:
            print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
            return None

        count = 0

        # wait until network is up in guest
        while not util.nmap_ssh():
            sleep(1)
            print('{0} Guest not ready'.format(count))
            count += 1

        # now backend is ready for connections
        print('Guest ready for SSH connections!')

        # TODO must store ip of guest here too
        self.guests.append({
            'domain': dom,
            'state': 'available'
        })

    def request_guest(self, src_ip):
        # check if there is a guest associated with src_ip
        with_ip = [g for g in self.guests if g['state'] == 'used' and g['ip'] == src_ip]
        if len(with_ip) > 0:
            guest = with_ip[0]
            guest['state'] = 'in_use'
            return guest['domain']

        # get an available guest
        available = [g for g in self.guests if g['state'] == 'available']
        if len(available) == 0:
            print('No guests available!')
            raise QemuError()

        guest = available[0]
        guest['state'] = 'in_use'
        guest['ip'] = src_ip
        return guest['domain']


