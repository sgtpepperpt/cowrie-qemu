import sys
import libvirt

import networkHandler


def initialise():
    # open connection to libvirt
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)

    # create a NAT for the guests
    network = networkHandler.create_network(conn)

    return conn, network


def destroy(conn, network):
    # destroy transient network
    network.destroy()

    # close libvirt connection
    conn.close()
