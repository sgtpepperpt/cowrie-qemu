import sys
import libvirt

import util


def create_network(connection):
    network_xml = util.read_file('config_files/default_network.xml')
    network_config = network_xml.format(network_name='cowrie',
                                        iface_name='virbr2',
                                        default_gateway='192.168.150.1',
                                        dhcp_range_start='192.168.150.127',
                                        dhcp_range_end='192.168.150.254',
                                        mac_address_0='aa:bb:cc:dd:ee:ff',
                                        ip_address_0='192.168.150.15')

    try:
        # create a transient virtual network
        net = connection.networkCreateXML(network_config)
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