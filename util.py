import subprocess
import time


def ping():
    out = subprocess.run(['ping', '-c 1', '192.168.150.15'], capture_output=True)
    return out.returncode == 0


def nmap_ssh(guest_ip):
    out = subprocess.run(['nmap', guest_ip, '-PN',  '-p ssh'], capture_output=True)
    return out.returncode == 0 and b'open' in out.stdout


def read_file(file_name):
    with open(file_name, 'r') as file:
        return file.read()


def generate_mac_ip(guest_id):
    # TODO support more
    mac = 'aa:bb:cc:dd:ee:' + hex(guest_id)[2:]
    ip = '192.168.150.' + str(guest_id)
    return mac, ip


def now():
    return time.time()