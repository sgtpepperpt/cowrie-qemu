# Copyright (c) 2019 Guilherme Borges <guilhermerosasborges@gmail.com>
# See the COPYRIGHT file for more information

import struct

from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor, threads

from pool_service import PoolService


class PoolServer(Protocol):
    def __init__(self, factory):
        self.factory = factory

    def dataReceived(self, data):
        res_op = struct.unpack('!c', bytes([data[0]]))[0]  # yes, this needs to be done to extract the op code correctly
        response = None

        if res_op == b'i':
            recv = struct.unpack('!II', data[1:])

            # set the pool service thread configs
            max_vm = recv[0]
            vm_unused_timeout = recv[1]
            self.factory.pool_service.set_configs(max_vm, vm_unused_timeout)

            # respond with ok
            self.factory.initialised = True
            response = struct.pack('!cI', b'i', 0)

        elif res_op == b'r':
            recv = struct.unpack('!H', data[1:3])
            ip_len = recv[0]

            recv = struct.unpack('!{0}s'.format(ip_len), data[3:])
            attacker_ip = recv[0]

            # TODO send same data for now
            vm_id = 100
            honey_ip = b'127.0.0.1'
            ssh_port = 2022
            telnet_port = 2023

            fmt = '!cIIH{0}sHH'.format(len(honey_ip))
            response = struct.pack(fmt, b'r', 0, vm_id, len(honey_ip), honey_ip, ssh_port, telnet_port)

        elif res_op == b'f':
            recv = struct.unpack('!I', data[1:])
            vm_id = recv[0]

            # free the vm
            pass

        if response:
            self.transport.write(response)


class PoolServerFactory(Factory):
    def __init__(self):
        self.initialised = False

        # configs, come from client
        self.max_vm = 0
        self.vm_unused_timeout = 0

        # pool handling
        self.pool_service = None

    def startFactory(self):
        # start the pool thread with default configs
        self.pool_service = PoolService()
        threads.deferToThread(self.pool_service.producer_loop)

    def buildProtocol(self, addr):
        print('Received connection from {0}:{1}'.format(addr.host, addr.port))
        return PoolServer(self)


endpoint = TCP4ServerEndpoint(reactor, 3574)
endpoint.listen(PoolServerFactory())
reactor.run()
