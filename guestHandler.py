import sys
import libvirt

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
