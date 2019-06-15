import sys
import libvirt

networkXML = '''
<network>
    <name>{networkName}</name>
    <forward mode='nat'/>
    <bridge name='{ifaceName}' stp='on' delay='0'/>
    <ip address='{defaultGateway}' netmask='255.255.255.0'>
        <dhcp>
            <range start='{dhcpRangeStart}' end='{dhcpRangeEnd}'/>
            <host mac='{macAddress0}' name='vm1' ip='{ipAddress0}'/>
        </dhcp>
    </ip>
</network>
'''


networkConfig = networkXML.format(networkName='cowrie',
                                  ifaceName='virbr2',
                                  defaultGateway='192.168.150.1',
                                  dhcpRangeStart='192.168.150.127',
                                  dhcpRangeEnd='192.168.150.254',
                                  macAddress0='aa:bb:cc:dd:ee:ff',
                                  ipAddress0='192.168.150.15')


def create_network(connection):
    try:
        # create a transient virtual network
        net = connection.networkCreateXML(networkConfig)
        if net is None:
            print('Failed to define a virtual network', file=sys.stderr)
            exit(1)

        # set the network active
        # not needed since apparently transient networks are created as active; uncomment if persistent
        # net.create()

        return net
    except libvirt.libvirtError as e:
        print(e)
        print('Network already exists')
        return connection.networkLookupByName('cowrie')