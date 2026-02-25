#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import re
import hashlib
import os
import sys

PACKAGES = [
    {'name': 'nordlayer', 'dir': '.'},
    {'name': 'nordlayer-bin', 'dir': 'nordlayer-bin'},
]


def parse_version(version_str):
    """Parse version string into tuple of integers for comparison."""
    try:
        return tuple(int(x) for x in version_str.split('.'))
    except (ValueError, AttributeError):
        return (0, 0, 0)


def get_latest_version():
    """Get the latest NordLayer version by scraping the help page, with API fallback."""
    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/58.0.3029.110 Safari/537.36'
    }

    try:
        response = requests.get(
            'https://help.nordlayer.com/docs/linux',
            headers=req_headers,
            timeout=15,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        toc = soup.find('nav', {'aria-label': 'Table of contents'})
        if toc:
            first_link = toc.find('a')
            if first_link:
                text = first_link.get_text(strip=True)
                match = re.search(r'Linux\s+(\d+\.\d+\.\d+)', text)
                if match:
                    return match.group(1)

        for header in soup.find_all(['h1', 'h2', 'h3']):
            text = header.get_text(strip=True)
            match = re.search(r'Linux\s+(\d+\.\d+\.\d+)', text)
            if match:
                return match.group(1)
    except requests.RequestException:
        pass

    try:
        resp = requests.get(
            'https://downloads.nordlayer.com/linux/latest/version', timeout=10
        )
        resp.raise_for_status()
        version = resp.text.strip()
        if re.match(r'^\d+\.\d+\.\d+$', version):
            return version
    except requests.RequestException:
        pass

    return None


def get_current_version(pkg_dir):
    """Read the current pkgver from PKGBUILD."""
    pkgbuild_path = os.path.join(pkg_dir, 'PKGBUILD')
    with open(pkgbuild_path, 'r') as f:
        for line in f:
            match = re.match(r'^pkgver=(.+)$', line)
            if match:
                return match.group(1).strip()
    return None


def update_pkgver(pkg_dir, version):
    """Update pkgver and reset pkgrel in PKGBUILD."""
    pkgbuild_path = os.path.join(pkg_dir, 'PKGBUILD')
    with open(pkgbuild_path, 'r') as f:
        pkgbuild = f.read()

    pkgbuild = re.sub(r'^pkgver=.*$', f'pkgver={version}', pkgbuild, flags=re.MULTILINE)
    pkgbuild = re.sub(r'^pkgrel=.*$', 'pkgrel=1', pkgbuild, flags=re.MULTILINE)

    with open(pkgbuild_path, 'w') as f:
        f.write(pkgbuild)

    print(f'  PKGBUILD pkgver updated to {version}.')


def download_deb(version):
    """Download the .deb package for the given version."""
    url = (
        f"https://downloads.nordlayer.com/linux/latest/debian/pool/main/"
        f"nordlayer_{version}_amd64.deb"
    )
    filename = f"nordlayer_{version}_amd64.deb"
    if os.path.exists(filename):
        print(f"  Using cached {filename}")
        return filename

    req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/58.0.3029.110 Safari/537.36'
    }
    response = requests.get(url, headers=req_headers, stream=True, timeout=120)
    response.raise_for_status()
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Downloaded {filename}")
    return filename


def calculate_checksum(filename):
    """Calculate SHA-512 checksum of a file."""
    sha512 = hashlib.sha512()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha512.update(chunk)
    return sha512.hexdigest()


def update_checksum(pkg_dir, checksum):
    """Update the SHA-512 checksum in PKGBUILD."""
    pkgbuild_path = os.path.join(pkg_dir, 'PKGBUILD')
    with open(pkgbuild_path, 'r') as f:
        pkgbuild = f.read()

    pkgbuild = re.sub(
        r"^sha512sums_x86_64=\('.*'\)$",
        f"sha512sums_x86_64=('{checksum}')",
        pkgbuild,
        flags=re.MULTILINE,
    )

    with open(pkgbuild_path, 'w') as f:
        f.write(pkgbuild)

    print('  Checksum updated in PKGBUILD.')


def generate_srcinfo(pkg_dir, checksum):
    """Generate .SRCINFO from PKGBUILD metadata without requiring makepkg."""
    pkgbuild_path = os.path.join(pkg_dir, 'PKGBUILD')
    srcinfo_path = os.path.join(pkg_dir, '.SRCINFO')

    with open(pkgbuild_path, 'r') as f:
        pkgbuild = f.read()

    def get_value(key):
        m = re.search(rf'^{key}=(.+)$', pkgbuild, re.MULTILINE)
        if not m:
            return None
        return m.group(1).strip().strip("'\"")

    def get_array(key):
        m = re.search(rf"^{key}=\((.+)\)$", pkgbuild, re.MULTILINE)
        if not m:
            return []
        return [v.strip().strip("'\"") for v in m.group(1).split("' '")]

    pkgname = get_value('pkgname')
    pkgdesc = get_value('pkgdesc')
    pkgver = get_value('pkgver')
    pkgrel = get_value('pkgrel')
    url = get_value('url')

    install = get_value('install')
    if install:
        install = install.replace('${pkgname}', pkgname)

    arches = get_array('arch')
    licenses = get_array('license')
    depends = get_array('depends')
    conflicts = get_array('conflicts')
    replaces = get_array('replaces')
    options = get_array('options')

    source_url = (
        f"https://downloads.nordlayer.com/linux/latest/debian/pool/main/"
        f"nordlayer_{pkgver}_amd64.deb"
    )

    lines = [f'pkgbase = {pkgname}']
    lines.append(f'\tpkgdesc = {pkgdesc}')
    lines.append(f'\tpkgver = {pkgver}')
    lines.append(f'\tpkgrel = {pkgrel}')
    lines.append(f'\turl = {url}')
    if install:
        lines.append(f'\tinstall = {install}')
    for arch in arches:
        lines.append(f'\tarch = {arch}')
    for lic in licenses:
        lines.append(f'\tlicense = {lic}')
    for dep in depends:
        lines.append(f'\tdepends = {dep}')
    for con in conflicts:
        lines.append(f'\tconflicts = {con}')
    for rep in replaces:
        lines.append(f'\treplaces = {rep}')
    for opt in options:
        lines.append(f'\toptions = {opt}')
    lines.append(f'\tsource_x86_64 = {source_url}')
    lines.append(f'\tsha512sums_x86_64 = {checksum}')
    lines.append('')
    lines.append(f'pkgname = {pkgname}')
    lines.append('')

    with open(srcinfo_path, 'w') as f:
        f.write('\n'.join(lines))

    print('  .SRCINFO updated.')


def clean_up(filename):
    if os.path.exists(filename):
        os.remove(filename)
        print(f"Removed temporary file {filename}")


def update_package(pkg, latest_version, checksum):
    """Update a single package."""
    pkg_name = pkg['name']
    pkg_dir = pkg['dir']

    print(f"\n[{pkg_name}]")

    current_version = get_current_version(pkg_dir)
    print(f'  Current version: {current_version}')

    if latest_version == current_version:
        print('  Already up to date.')
        return False

    if parse_version(latest_version) < parse_version(current_version):
        print(f'  Detected version ({latest_version}) is older than current ({current_version}).')
        print('  Refusing to downgrade.')
        return False

    print(f'  Updating {current_version} -> {latest_version}')
    update_pkgver(pkg_dir, latest_version)
    update_checksum(pkg_dir, checksum)
    generate_srcinfo(pkg_dir, checksum)
    return True


if __name__ == '__main__':
    latest_version = get_latest_version()
    if not latest_version:
        print('Could not determine the latest version.')
        sys.exit(1)

    print(f'Latest upstream version: {latest_version}')

    deb_filename = None
    checksum = None
    any_updated = False

    for pkg in PACKAGES:
        current = get_current_version(pkg['dir'])
        if current != latest_version and parse_version(latest_version) > parse_version(current):
            if deb_filename is None:
                print(f"\nDownloading .deb for version {latest_version}...")
                deb_filename = download_deb(latest_version)
                checksum = calculate_checksum(deb_filename)
                print(f"  Checksum: {checksum[:16]}...")
            break

    for pkg in PACKAGES:
        if checksum:
            updated = update_package(pkg, latest_version, checksum)
            if updated:
                any_updated = True
        else:
            print(f"\n[{pkg['name']}]")
            current = get_current_version(pkg['dir'])
            print(f'  Current version: {current}')
            if current == latest_version:
                print('  Already up to date.')
            elif parse_version(latest_version) < parse_version(current):
                print(f'  Refusing to downgrade from {current} to {latest_version}.')

    if deb_filename:
        clean_up(deb_filename)

    if any_updated:
        print('\nAll updates completed successfully.')
    else:
        print('\nNo updates needed.')
