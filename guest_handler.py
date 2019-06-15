import sys
import libvirt

import util


def create_guest(connection, disk_img):
    guest_xml = util.read_file('config_files/default_guest.xml')
    guest_config = guest_xml.format(guest_name='ubuntu18.04-experimental',
                                    disk_image=disk_img,
                                    mac_address='aa:bb:cc:dd:ee:ff',
                                    network_name='cowrie')

    try:
        dom = connection.createXML(guest_config, 0)
        if dom is None:
            print('Failed to create a domain from an XML definition.', file=sys.stderr)
            exit(1)

        print('Guest '+dom.name()+' has booted', file=sys.stderr)
        return dom
    except libvirt.libvirtError as e:
        print(e)
        print('Guest already booted')
        return connection.lookupByName('ubuntu18.04-experimental')
