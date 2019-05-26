import subprocess


def ping():
    out = subprocess.run(['ping', '-c 1', '192.168.150.15'], capture_output=True)
    return out.returncode == 0


def nmap_ssh():
    out = subprocess.run(['nmap', '192.168.150.15', '-PN',  '-p ssh'], capture_output=True)
    return out.returncode == 0 and b'open' in out.stdout