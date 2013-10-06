#!/usr/bin/python


# Author Humble Chirammal <humble.devassy@gmail.com> | <hchiramm@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.



import os
import sys
import hooking
import traceback

'''

macbind:

syntax:
macbind=macaddress-brName-portType,...
refer README for more details.


if 'ovs' as portType:

<interface type='bridge'>
 <mac address='00:1a:4a:41:d2:5f'/>
 <source bridge='ovsbr0'/>
 <model type='virtio'/>
 <virtualport type='openvswitch'/>
 <filterref filter='vdsm-no-mac-spoofing'/>
 <link state='up'/>
 <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
</interface>

If 'lb' or '' as portType:
The given bridge will be replaced with current bridge:

<interface type='bridge'>
  <mac address='00:1a:4a:41:d2:b8'/>
  <source bridge='br0'/>
  <model type='virtio'/>
  <filterref filter='vdsm-no-mac-spoofing'/>
  <link state='up'/>
  <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>
</interface>

'''


def createVportElement(domxml, porttype):
    vPort = domxml.createElement('virtualport')
    vPort.setAttribute('type', 'openvswitch')
    return vPort


def createSbridgeElement(domxml, brName):
    sBridge = domxml.createElement('source')
    sBridge.setAttribute('bridge', brName)
    return sBridge


def removeElement(interface, Element):
    interface.removeChild(Element)


if 'macbind' in os.environ:
    try:

        macbinds = os.environ['macbind']
        domxml = hooking.read_domxml()
        macAddr = ''
        brName = ''
        pType = ''

        for nic in macbinds.split(','):
            try:
                macAddr, brName, pType = nic.split('-')
                macAddr = macAddr.strip()
                brName = brName.strip()
                pType = pType.strip()

            except ValueError:
                sys.stderr.write('macbind: input error, expected '
                                 'macbind:macAddr:brName:pType,'
                                 'where brName is bridgename'
                                 'pType can be ovs|lb')
                sys.exit(2)
            if pType == "ovs":
                command = ['/usr/bin/ovs-vsctl', 'br-exists %s' % (brName)]
                retcode, out, err = hooking.execCmd(
                    command, sudo=False, raw=True)
                if retcode != 0:
                    sys.stderr.write('macbind: Error in finding ovsbridge:'
                                     '%s: %s, err = %s' %
                                     (brName, ' '.join(command), err))
                    continue
            if pType == "lb" or pType == '':
                command = ['/usr/sbin/brctl', 'show', brName]
                retcode, out, err = hooking.execCmd(
                    command, sudo=False, raw=True)

                if err or retcode != 0:
                    sys.stderr.write('macbind: Error in finding Linuxbridge:'
                                     ' %s \n: %s, err = %s\n' %
                                    (brName, ' '.join(command), err))
                    continue

            for interface in domxml.getElementsByTagName('interface'):
                for macaddress in interface.getElementsByTagName('mac'):
                    addr = macaddress.getAttribute('address')
                    if addr == macAddr:
                        for bridge in interface.getElementsByTagName('source'):
                            interface.removeChild(bridge)
                            interface.appendChild(
                                createSbridgeElement(domxml, brName))
                            if pType == "ovs":
                                interface.appendChild(
                                    createVportElement(domxml, 'openvswitch'))

        hooking.write_domxml(domxml)
    except:
        sys.stderr.write('macbind: [unexpected error]: %s\n' %
                         traceback.format_exc())
        sys.exit(2)
