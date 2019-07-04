# Copyright (c) 2019 Guilherme Borges <guilhermerosasborges@gmail.com>
# See the COPYRIGHT file for more information

from threading import Lock
import util
import os

from qemu_service import QemuService


class NoAvailableVMs(Exception):
    pass


class PoolService:
    """
    VM States:
        created -> available -> using -> used -> unavailable -> destroyed

        created:     initialised but not fully booted by Qemu
        available:   can be requested
        using:       a client is connected, can be served for other clients from same ip
        used:        client disconnectec, but can still be served for its ip
        unavailable: marked for destruction after timeout
        destroyed:   deleted by qemu, can be removed from list

    A lock is required to manipulate VMs in states [available, using, used], since these are the ones that can be
    accessed by several consumers and the producer. All other states are accessed only by the single producer.
    """
    def __init__(self):
        self.qemu = QemuService()
        self.guests = []
        self.guest_id = 2
        self.guest_lock = Lock()

        # default configs
        self.max_vm = 2
        self.vm_unused_timeout = 600

        # cleanup older qemu objects
        self.qemu.destroy_all_guests()
        self.qemu.destroy_all_networks()
        self.qemu.destroy_all_network_filters()

        # initialise qemu environment
        self.qemu.initialise_environment()

    def __del__(self):
        print('Trying clean shutdown')

        self.guest_lock.acquire()
        try:
            running_guests = [g for g in self.guests if g['state'] != 'destroyed']
            for guest in running_guests:
                self.qemu.destroy_guest(guest['domain'], guest['snapshot'])
                guest['state'] = 'destroyed'
        finally:
            self.guest_lock.release()

        # force destroy remaining stuff
        self.qemu.destroy_all_guests()
        self.qemu.destroy_all_networks()
        self.qemu.destroy_all_network_filters()

    def set_configs(self, max_vm, vm_unused_timeout):
        self.max_vm = max_vm
        self.vm_unused_timeout = vm_unused_timeout

    def get_vm_states(self, states):
        return [g for g in self.guests if g['state'] in states]

    def existing_pool_size(self):
        return len([g for g in self.guests if g['state'] != 'destroyed'])

    # Producers
    def __producer_mark_timed_out(self, vm_timeout):
        """
        Checks timed-out VMs and acquires lock to safely mark for deletion
        """
        self.guest_lock.acquire()
        try:
            for vm in self.guests:
                timed_out = vm['freed_timestamp'] + vm_timeout * 1000 < util.now()

                # only mark VMs not in use
                if vm['state'] == 'used' and timed_out:
                    vm['state'] = 'unavailable'
        finally:
            self.guest_lock.release()

    def __producer_destroy_timed_out(self):
        unavailable_vms = self.get_vm_states(['unavailable'])
        for vm in unavailable_vms:
            try:
                self.qemu.destroy_guest(vm['domain'], vm['snapshot'])
                os.remove(vm['snapshot'])
                vm['state'] = 'destroyed'
            except Exception:
                pass

    def __producer_remove_destroyed(self):
        for vm in self.guests:
            if vm['state'] == 'destroyed':
                self.guests.remove(vm)

    def __producer_mark_available(self):
        created_guests = self.get_vm_states(['created'])
        for guest in created_guests:
            if util.nmap_ssh(guest['guest_ip']):
                guest['state'] = 'available'
                print('Guest {0} ready for SSH connections @ {1}!'.format(guest['id'], guest['guest_ip']))

    def producer_loop(self):
        while True:
            # delete old VMs, but do not let pool size be 0
            if self.existing_pool_size() > 1:
                # mark timed-out VMs for destruction
                self.__producer_mark_timed_out(self.vm_unused_timeout)

                # delete timed-out VMs
                self.__producer_destroy_timed_out()

                # remove destroyed from list
                self.__producer_remove_destroyed()

            # replenish pool until full
            create = self.max_vm - self.existing_pool_size()
            for _ in range(create):
                dom, snap, guest_ip = self.qemu.create_guest(self.guest_id)

                self.guests.append({
                    'id': self.guest_id,
                    'state': 'created',
                    'guest_ip': guest_ip,
                    'connected': 0,
                    'client_ips': set(),
                    'freed_timestamp': -1,
                    'domain': dom,
                    'snapshot': snap
                })

                self.guest_id += 1

            # check for created VMs that can become available
            self.__producer_mark_available()

    # Consumers
    def __consumers_get_vm_ip(self, src_ip):
        self.guest_lock.acquire()
        try:
            for vm in self.guests:
                # if ip is the same, doesn't matter if being used or not
                if src_ip in vm['client_ips'] and vm['state'] in ['used', 'using']:
                    return vm
        finally:
            self.guest_lock.release()

        return None

    def __consumers_get_available_vm(self):
        self.guest_lock.acquire()
        try:
            for vm in self.guests:
                if vm['state'] == 'available':
                    return vm
        finally:
            self.guest_lock.release()

        return None

    def __consumers_get_any_vm(self):
        self.guest_lock.acquire()
        try:
            # try to get a VM with few clients
            least_conn = None

            usable_guests = self.get_vm_states(['using', 'used'])
            for vm in usable_guests:
                if not least_conn or vm['connected'] < least_conn['connected']:
                    least_conn = vm

            return least_conn
        finally:
            self.guest_lock.release()

    # Consumer methods to be called concurrently
    def request_vm(self, src_ip):
        share_vm = True  # TODO config

        # first check if there is one for the ip
        vm = self.__consumers_get_vm_ip(src_ip)

        # try to get an available VM
        if not vm:
            vm = self.__consumers_get_available_vm()

        # or get any other if policy is to share VMs
        if not vm and share_vm:
            vm = self.__consumers_get_any_vm()
        else:
            raise NoAvailableVMs()

        vm['state'] = 'using'
        vm['connected'] += 1
        vm['client_ips'].add(src_ip)

        return vm['id'], vm['ip']

    def free_vm(self, vm_id):
        self.guest_lock.acquire()
        try:
            for vm in self.guests:
                if vm['id'] == vm_id:
                    vm['state'] = 'used'
                    vm['freed_timestamp'] = util.now()
                    vm['connected'] -= 1
                    return
        finally:
            self.guest_lock.release()
