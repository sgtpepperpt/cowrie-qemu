import os
import sys
import libvirt
import shutil
import getpass
import subprocess
import random
from time import sleep

guestXML = '''
<domain type='qemu'>
    <name>{guestName}</name>
    <memory unit='KiB'>2097152</memory>
    <currentMemory unit='KiB'>2097152</currentMemory>
    <vcpu placement='static'>4</vcpu>
    <os>
        <type arch='x86_64' machine='pc-q35-3.1'>hvm</type>
        <boot dev='hd'/>
    </os>
    <features>
        <acpi/>
        <apic/>
        <vmport state='off'/>
    </features>
    <on_poweroff>destroy</on_poweroff>
    <on_reboot>restart</on_reboot>
    <on_crash>destroy</on_crash>
    <pm>
        <suspend-to-mem enabled='no'/>
        <suspend-to-disk enabled='no'/>
    </pm>

    <devices>
        <emulator>/usr/bin/qemu-system-x86_64</emulator>

        <disk type='file' device='disk'>
            <driver name='qemu' type='qcow2'/>
            <source file='{diskImage}'/>
            <target dev='vda' bus='virtio'/>
            <address type='pci' domain='0x0000' bus='0x03' slot='0x00' function='0x0'/>
        </disk>

        <controller type='sata' index='0'>
            <address type='pci' domain='0x0000' bus='0x00' slot='0x1f' function='0x2'/>
        </controller>

        <controller type='pci' index='0' model='pcie-root'/>

        <controller type='virtio-serial' index='0'>
            <address type='pci' domain='0x0000' bus='0x02' slot='0x00' function='0x0'/>
        </controller>
        
        <controller type='pci' index='6' model='pcie-root-port'>
            <model name='pcie-root-port'/>
            <target chassis='6' port='0x15'/>
            <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x5'/>
        </controller>

        <interface type='network'>
            <start mode='onboot'/>
            <mac address='{macAddress}'/>
            <source network='{networkName}'/>
            <model type='virtio'/>
            <address type='pci' domain='0x0000' bus='0x01' slot='0x00' function='0x0'/>
        </interface>

        <serial type='pty'>
            <target type='isa-serial' port='0'>
                <model name='isa-serial'/>
            </target>
        </serial>

        <console type='pty'>
            <target type='serial' port='0'/>
        </console>

        <channel type='unix'>
            <target type='virtio' name='org.qemu.guest_agent.0'/>
            <address type='virtio-serial' controller='0' bus='0' port='1'/>
        </channel>

        <graphics type='spice' autoport='yes'>
            <listen type='address'/>
            <image compression='off'/>
        </graphics>

        <video>
            <model type='qxl' ram='65536' vram='65536' vgamem='16384' heads='1' primary='yes'/>
            <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x0'/>
        </video>

        <channel type='spicevmc'>
            <target type='virtio' name='com.redhat.spice.0'/>
            <address type='virtio-serial' controller='0' bus='0' port='2'/>
        </channel>

        <redirdev bus='usb' type='spicevmc'>
            <address type='usb' bus='0' port='2'/>
        </redirdev>

        <redirdev bus='usb' type='spicevmc'>
            <address type='usb' bus='0' port='3'/>
        </redirdev>

        <memballoon model='virtio'>
            <address type='pci' domain='0x0000' bus='0x04' slot='0x00' function='0x0'/>
        </memballoon>

        <rng model='virtio'>
            <backend model='random'>/dev/urandom</backend>
            <address type='pci' domain='0x0000' bus='0x05' slot='0x00' function='0x0'/>
        </rng>
    </devices>
</domain>
'''

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

snapshotXML = '''
<domainsnapshot>
    <memory snapshot='no'/>
    <disks>
        <disk name='/var/lib/libvirt/images/ubuntu18.04.qcow2'>
            <driver type='qcow2'/>
            <source file='/var/lib/libvirt/images/ubuntu18.04snapshot.qcow2'/>
        </disk>
    </disks>
</domainsnapshot>
'''


networkConfig = networkXML.format(networkName='cowrie',
                                  ifaceName='virbr2',
                                  defaultGateway='192.168.150.1',
                                  dhcpRangeStart='192.168.150.127',
                                  dhcpRangeEnd='192.168.150.254',
                                  macAddress0='aa:bb:cc:dd:ee:ff',
                                  ipAddress0='192.168.150.15')


def create_guest(connection, diskImg):
    guestConfig = guestXML.format(guestName='ubuntu18.04-experimental',
                                  diskImage=diskImg,
                                  macAddress='aa:bb:cc:dd:ee:ff',
                                  networkName='cowrie')

    try:
        dom = connection.createXML(guestConfig, 0)
        if dom is None:
            print('Failed to create a domain from an XML definition.', file=sys.stderr)
            exit(1)

        print('Guest '+dom.name()+' has booted', file=sys.stderr)
        return dom
    except libvirt.libvirtError as e:
        print(e)
        print('Guest already booted')
        return connection.lookupByName('ubuntu18.04-experimental')


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


def tests(dom, network):
    type = dom.info()
    print('The name of the domain is "' + str(type) + '".')

    # print(dom.XMLDesc())

    flag = dom.hasCurrentSnapshot()
    print('The value of the current snapshot flag is ' + str(flag))


def ping():
    out = subprocess.run(['ping', '-c 1', '192.168.150.15'], capture_output=True)
    return out.returncode == 0


def nmap_ssh():
    out = subprocess.run(['nmap', '192.168.150.15', '-PN',  '-p ssh'], capture_output=True)
    return out.returncode == 0 and b'open' in out.stdout


def create_disk_snapshot(source_img, destination_img):
    # s = domain.listAllSnapshots()
    # ret = domain.snapshotCreateXML(snapshotXML, libvirt.VIR_DOMAIN_SNAPSHOT_CREATE_DISK_ONLY)

    shutil.chown(source_img, getpass.getuser())
    out = subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-b', source_img, destination_img], capture_output=True)
    return out.returncode == 0


def generate_image_path(base_path, image_tag):
    while True:
        seed = random.getrandbits(32)
        path = base_path + 'snapshot-{0}-{1}-qcow2.img'.format(image_tag, seed)
        if not os.path.isfile(path):
            return path


def main():
    # open connection to libvirt
    conn = libvirt.open('qemu:///system')
    if conn is None:
        print('Failed to open connection to qemu:///system', file=sys.stderr)
        exit(1)

    # create a NAT for the guests
    network = create_network(conn)

    # create a disk snapshot to be used by the guest
    source_img = '/home/gb/Repositories/qemu/ubuntu18.04.qcow2'
    destination_img = generate_image_path('/home/gb/Repositories/qemu/', 'ubuntu18.04')
    if not create_disk_snapshot(source_img, destination_img):
        print('There was a problem creating the disk snapshot.', file=sys.stderr)
        exit(1)

    # create a single guest
    dom = create_guest(conn, destination_img)
    if dom is None:
        print('Failed to find the domain ' + 'QEmu-ubuntu', file=sys.stderr)
        exit(1)

    # use guest
    tests(dom, network)

    # wait until network is up in guest
    while not nmap_ssh():
        sleep(1)
        print('Guest not ready')

    # now backend is ready for connections

    # destroy created guest
    dom.destroy()

    # destroy its disk snapshot
    os.remove(destination_img)

    # destroy transient network
    network.destroy()

    # close libvirt connection
    conn.close()


main()
