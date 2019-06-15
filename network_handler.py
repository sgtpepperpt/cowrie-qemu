import sys
import libvirt

import util


def create_network(connection):
    network_xml = util.read_file('config_files/default_network.xml')

    sample_host = '<host mac=\'{mac_address}\' name=\'{name}\' ip=\'{ip_address}\'/>\n'
    hosts = ''

    for i in range(2, 255):
        mac_address = 'aa:bb:cc:dd:ee:' + hex(i)[2:]
        vm_name = 'vm' + str(i)
        ip_address = '192.168.150.' + str(i)
        hosts += sample_host.format(mac_address=mac_address, name=vm_name, ip_address=ip_address)

    network_config = network_xml.format(network_name='cowrie',
                                        iface_name='virbr2',
                                        default_gateway='192.168.150.1',
                                        dhcp_range_start='192.168.150.2',
                                        dhcp_range_end='192.168.150.254',
                                        hosts=hosts)

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