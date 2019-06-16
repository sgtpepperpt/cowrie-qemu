import sys
import libvirt
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

        # data structs
        self.guests = []
        self.guest_id = 2

    def __del__(self):
        self.network.destroy()  # destroy transient network
        self.conn.close()  # close libvirt connection

        print('Connection to Qemu closed successfully')

    def create_guest(self):
        guest_mac, guest_ip = util.generate_mac_ip(self.guest_id)
        unique_id = uuid.uuid4().hex

        # create a single guest
        dom, snapshot = guest_handler.create_guest(self.conn, guest_mac, unique_id)
        if dom is None:
            print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
            return None

        count = 0

        # wait until network is up in guest
        while not util.nmap_ssh(guest_ip):
            sleep(1)
            print('{0} Guest not ready'.format(count))
            count += 1

        # now backend is ready for connections
        print('Guest ready for SSH connections!')

        self.guests.append({
            'id': self.guest_id,
            'domain': dom,
            'snapshot': snapshot,
            'state': 'available',
            'ip': guest_ip
        })

        self.guest_id += 1

    def request_guest(self, src_ip):
        # check if there is a guest associated with src_ip
        with_ip = [g for g in self.guests if g['state'] == 'used' and g['client_ip'] == src_ip]
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
        guest['client_ip'] = src_ip
        return guest['id'], guest['ip']

    def free_guest(self, guest_id):
        guest = [g for g in self.guests if g['id'] == guest_id]
        if len(guest) == 0:
            return

        guest[0]['state'] = 'used'
        guest[0]['timestamp'] = util.now()

    def available_guests(self):
        return len([g for g in self.guests if g['state'] == 'available'])

    def destroy_guest(self, guest_id):
        guest = [g for g in self.guests if g['id'] == guest_id]
        if len(guest) == 0:
            return

        guest[0]['state'] = 'destroyed'
        guest_handler.destroy_guest(guest[0]['domain'], guest[0]['snapshot'])
