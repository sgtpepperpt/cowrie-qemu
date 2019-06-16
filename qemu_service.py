import sys
import libvirt
import os
import uuid
import util

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
        """
        Returns an unready domain and its snapshot information
        """
        guest_mac, guest_ip = util.generate_mac_ip(guest_id)
        unique_id = uuid.uuid4().hex

        # create a single guest
        dom, snapshot = guest_handler.create_guest(self.conn, guest_mac, unique_id)
        if dom is None:
            print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
            return None

        return dom, snapshot, guest_ip

    def destroy_guest(self, domain, snapshot):
        try:
            domain.destroy()
            os.remove(snapshot)  # destroy its disk snapshot
        except Exception as error:
            print(error)

    def destroy_all_guests(self):
        domains = self.conn.listDomainsID()
        if not domains:
            print('Could not get domain list', file=sys.stderr)

        for domain_id in domains:
            d = self.conn.lookupByID(domain_id)
            if d.name().startswith('cowrie'):
                d.destroy()
