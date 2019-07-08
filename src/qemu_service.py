# Copyright (c) 2019 Guilherme Borges <guilhermerosasborges@gmail.com>
# See the COPYRIGHT file for more information

import sys
import libvirt
import os
import uuid

import guest_handler
import network_handler
import util


class QemuError(Exception):
    pass


class QemuService:
    def __init__(self):
        # open connection to libvirt
        self.conn = libvirt.open('qemu:///system')
        if self.conn is None:
            print('Failed to open connection to qemu:///system', file=sys.stderr)
            raise QemuError()

        self.filter = None
        self.network = None

        print('Connection to Qemu established')

    def __del__(self):
        self.network.destroy()  # destroy transient network
        self.filter.undefine()  # destroy network filter
        self.conn.close()  # close libvirt connection

        print('Connection to Qemu closed successfully')

    def initialise_environment(self):
        """
        Initialises Qemu/libvirt environment needed to run guests. Namely starts networks and network filters.
        """
        # create a network filter
        self.filter = network_handler.create_filter(self.conn)

        # create a NAT for the guests
        self.network = network_handler.create_network(self.conn)

    def create_guest(self, guest_id):
        """
        Returns an unready domain and its snapshot information
        """
        # configs
        base_image = '/home/gb/Repositories/qemu/ubuntu18.04-libvirt.qcow2'
        snapshot_dir = '/home/gb/Repositories/qemu/'

        # generate networking details
        guest_mac, guest_ip = util.generate_mac_ip(guest_id)
        guest_unique_id = uuid.uuid4().hex

        # create a single guest
        dom, snapshot = guest_handler.create_guest(self.conn, guest_mac, guest_unique_id, base_image, snapshot_dir)
        if dom is None:
            print('Failed to create guest', file=sys.stderr)
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

    def destroy_all_networks(self):
        networks = self.conn.listNetworks()
        if not networks:
            print('Could not get network list', file=sys.stderr)

        for network in networks:
            if network.startswith('cowrie'):
                n = self.conn.networkLookupByName(network)
                n.destroy()

    def destroy_all_network_filters(self):
        network_filters = self.conn.listNWFilters()
        if not network_filters:
            print('Could not get network filters list', file=sys.stderr)

        for nw_filter in network_filters:
            if nw_filter.startswith('cowrie'):
                n = self.conn.nwfilterLookupByName(nw_filter)
                n.undefine()
