import struct

from twisted.internet.protocol import Protocol
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet import reactor


class PoolManager(Protocol):
    def __init__(self, factory):
        self.factory = factory

    def dataReceived(self, data):
        res_op = struct.unpack('!c', bytes([data[0]]))[0]  # yes, this needs to be done to extract the op code correctly
        response = None

        if res_op == b'i':
            recv = struct.unpack('!II', data[1:])

            # store received configs in global state
            self.factory.max_vm = recv[0]
            self.factory.vm_unused_timeout = recv[1]
            self.factory.initialised = True

            # respond with ok
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


class PoolManagerFactory(Factory):
    def __init__(self):
        self.initialised = False
        self.max_vm = 0
        self.vm_unused_timeout = 0

    def buildProtocol(self, addr):
        print('Received connection from {0}:{1}'.format(addr.host, addr.port))
        return PoolManager(self)


endpoint = TCP4ServerEndpoint(reactor, 3574)
endpoint.listen(PoolManagerFactory())
reactor.run()
