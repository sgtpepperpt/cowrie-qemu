from asyncio import Lock
import util
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
            if util.nmap_ssh(guest['ip']):
                guest['state'] = 'available'

    def producerLoop(self, max_vm, vm_timeout):
        while True:
            # delete old VMs, but do not let pool size be 0
            if self.existing_pool_size() > 1:
                # mark timed-out VMs for destruction
                self.__producer_mark_timed_out(vm_timeout)

                # delete timed-out VMs
                self.__producer_destroy_timed_out()

                # remove destroyed from list
                self.__producer_remove_destroyed()

            # replenish pool until full
            create = max_vm - self.existing_pool_size()
            for _ in range(create):
                dom, snap = self.qemu.create_guest()

                self.guests.append({
                    'id': self.guest_id,
                    'state': 'created',  # TODO change to created until boot complete signaled in callback
                    'connected': 0,
                    'ips': set(),
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
                if src_ip in vm['ips'] and vm['state'] in ['used', 'using']:
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
        vm['ips'].add(src_ip)

        return vm['id'], vm['ip']

    def free_vm(self, vm_id):
        self.guest_lock.acquire()
        try:
            for vm in self.guests:
                if vm['id'] == vm_id:
                    vm['state'] = 'used'
                    vm['freed_timestamp'] = util.now()
                    vm['connected'] -= 1
        finally:
            self.guest_lock.release()
