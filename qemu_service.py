import sys
import libvirt
import os
import uuid
import util
from time import sleep

import guest_handler
import network_handler


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

    def __del__(self):
        self.network.destroy()  # destroy transient network
        self.conn.close()  # close libvirt connection

        print('Connection to Qemu closed successfully')

    def create_guest(self, guest_id):
        guest_mac, guest_ip = util.generate_mac_ip(guest_id)
        unique_id = uuid.uuid4().hex

        # create a single guest
        dom, snapshot = guest_handler.create_guest(self.conn, guest_mac, unique_id)
        if dom is None:
            print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
            return None

        # wait until network is up in guest
        count = 0
        while not util.nmap_ssh(guest_ip):
            sleep(1)
            print('{0} Guest not ready'.format(count))
            count += 1

        # now backend is ready for connections
        print('Guest ready for SSH connections!')

        return dom, snapshot

    def destroy_guest(self, domain, snapshot):
        try:
            domain.destroy()
            os.remove(snapshot)  # destroy its disk snapshot
        except Exception as error:
            print(error)
