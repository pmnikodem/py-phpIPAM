#! /usr/bin/env python
__author__ = 'michaelluich'
author_email = 'mluich@stonesrose.com',

import requests
from requests.auth import HTTPBasicAuth
import json
import inspect

requests.packages.urllib3.disable_warnings()

import logging
logger = logging.getLogger(__name__)

class phpIPAM(object):
    """An interface to phpIPAM web API."""

    def __init__(self, server, app_id, username, password, ssl_verify=True, debug=False):
        """Parameters:
        server: the base server location.
        app_id: the app ID to access
        username: username
        password: password
        ssl_verify: should the certificate being verified"""
        self.error = 0
        self.error_message = ""
        self.server = server
        self.app_id = app_id
        self.username = username
        self.password = password
        self.appbase = "%s/api/%s" %(self.server,self.app_id)
        self.ssl_verify = ssl_verify
        self.token = None
        if debug:
            self.enable_debug()
        self.login()

    def enable_debug(self):
        try:
            import http.client as http_client
        except ImportError:
            # Python 2
            import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def __query(self, entrypoint, method=requests.get, data=None, auth=None):
        headers = {}
        if self.token:
            headers['token'] = self.token
        if data != None:
            if type(data) != str: data = json.dumps(data)
            headers['Content-Type'] = 'application/json'
            if method == requests.get:
                method = requests.post

        p = method(
            self.appbase + entrypoint,
            data=data,
            headers=headers,
            auth=auth,
            verify=self.ssl_verify
        )
        response = json.loads(p.text)
        callingfct = inspect.getouterframes(inspect.currentframe(), 2)[1][3]

        if not p.status_code in (200, 201):
            logging.error("phpipam.%s: Failure %s" % (callingfct, p.status_code))
            logging.error(response)
            self.error = p.status_code
            self.error_message = response['message']
            raise requests.exceptions.HTTPError(response=response)

        if not response['success']:
            logging.error("phpipam.%s: FAILURE: %s" % (callingfct, response['code']))
            self.error = response['code']
            raise requests.exceptions.HTTPError(response=response)

        logging.info("phpipam.%s: success %s" % (callingfct, response['success']))
        if 'data' in response:
            return response['data']
        else:
            return response


    # Authentication

    def login(self):
        "Login to phpIPAM and get a token."
        ticketJson = self.__query('/user/', auth=HTTPBasicAuth(self.username, self.password), method=requests.post)
        # Ok So now we have a token!
        self.token = ticketJson['token']
        self.token_expires= ticketJson['expires']
        logging.info("phpipam.login: Sucessful Login to %s" %(self.server))
        logging.debug("phpipam.login: IPAM Ticket expiration: %s" %(self.token_expires))
        return {"expires":self.token_expires}


    def ticket_check(self):
        "check if a ticket is still valid"
        try:
            return self.__query("/user/")
        except:
            return self.login()

    def ticket_extend(self):
        "Extends ticket duration (ticket last for 6h)"
        return self.__query("/user/")


    # Authorization

    def authorization(self, controller):
        "Check the authorization of a controller and get a list of methods"
        return self.__query("/%s/" %(controller))['methods']

    ### Controllers

    ## Sections

    def sections_get_all(self):
        "Get a list of all sections"
        return self.__query("/sections/")

    def sections_get_id(self, section):
        """Get the ID of a section

        Parameters:
            section: The name of the section you are looking for
        """
        return self.__query("/sections/%s/" % (section))['id']

    def sections_get(self, section_id):
        """Get the details for a specific section

        Parameters:
            section_id = section identifier. Can be the id number or name.
        """
        return self.__query("/sections/%s/" %(section_id))

    def sections_get_subnets(self, section_id):
        """Get the subnets for a specific section

         Parameters:
             section_id = section identifier. Can be the id number or name.
         """
        return self.__query("/sections/%s/subnets/" % (section_id))

    def sections_create(self, section_id, masterSection=0):
        """Create a section

         Parameters:
             section_id = section name.
         """
        data = {'name': section_id}
        if masterSection != 0 : data['masterSection'] = masterSection
        return self.__query("/sections/", data=data)

    def sections_delete(self, section_id,):
        """Delete a section

        Parameters:
        section_id = section name or id.
        """
        return self.__query("/sections/%s/" %(section_id), method=requests.delete)

    ## Subnet

    def subnet_get(self, subnet_id):
        """Get Information about a specific subnet

        Parameters:
        subnet_id: The subnet identifier
        """
        return self.__query("/subnets/%s/" % (subnet_id))

    def subnet_get_usage(self, subnet_id):
        """Get subnet usage

        Parameters:
        subnet_id: The subnet identifier
        """
        return self.__query("/subnets/%s/usage/" % (subnet_id))

    def subnet_get_first_free(self, subnet_id):
        """Get first free IP address in subnet

        Parameters:
        subnet_id: The subnet identifier
        """
        return self.__query("/subnets/%s/first_free/" % (subnet_id))

    def subnet_get_slaves(self, subnet_id):
        """Get all immediate slave subnets

        Parameters:
        subnet_id: The subnet identifier
        """
        return self.__query("/subnets/%s/slaves/" % (subnet_id))

    def subnet_all(self, subnet_id):
        """Get all addresses in a subnet

        Parameters:
        subnet_id: The subnet id
        """
        return self.__query("/subnets/%s/addresses/" % (subnet_id))

    def subnet_get_ip(self, subnet_id, ip_addr):
        """Get IP address from subnet

        Parameters:
        subnet_id: The subnet identifier
        ip_addr: IP address in dotted decimal format
        """
        return self.__query("/subnets/%s/addresses/%s/" % (subnet_id, ip_addr))

    def subnet_get_available_subnet(self, subnet_id, netmask):
        """Get first available subnet with specified netmask

        Parameters:
        subnet_id: The subnet identifier of the parent subnet
        netmask: desired subnet size
        """
        return self.__query("/subnets/%s/first_subnet/%s/" % (subnet_id, netmask))

    def subnet_get_available_subnet_all(self, subnet_id, netmask):
        """Get all available subnets with specified netmask

        Parameters:
        subnet_id: The subnet identifier of the parent subnet
        netmask: desired subnet size
        """
        return self.__query("/subnets/%s/all_subnets/%s/" % (subnet_id, netmask))

    def subnet_get_custom_fields(self):
        """Get all subnet custom fields
        """
        return self.__query("/subnets/custom_fields/")

    def subnet_search(self, subnet_id):
        """Search by cidr

        Parameters:
        subnet_id: The subnet cidr
        """
        return self.__query("/subnets/cidr/%s/" % (subnet_id))

    def subnet_create(self, subnet, mask, sectionId, description="", vlanid=None, mastersubnetid=0, nameserverid=None):
        """Create new subnet

        Parameters:
        subnet: The subnet
        mask: the subnet mask
        sectionId
        description: description
        vlanid:
        mastersubnetid:
        nameserverid:"""
        data={
            'subnet' : subnet,
            'mask' : mask,
            "sectionId" : sectionId,
            'description' : description,
            'vlanId' : vlanid,
            'masterSubnetId' : mastersubnetid,
            'nameserverId' : nameserverid
        }
        return self.__query("/subnets/", data=data)

    def subnet_create_child(self, mask, description="", vlanid=None, mastersubnetid=0, nameserverid=None):
        """Create new subnet of specific size as the first available in specified master subnet

        Parameters:
        mask: the subnet mask
        description: description
        vlanid:
        mastersubnetid:
        nameserverid:"""
        data={
            'description' : description,
            'vlanId' : vlanid,
            'nameserverId' : nameserverid
        }
        return self.__query("/subnets/%s/first_subnet/%s/" % (mastersubnetid, mask), data=data)

    def subnet_delete(self, subnet_id, ):
        """Delete a subnet

        Parameters:
        subnet_id = subnet name or id.
        """
        return self.__query("/subnets/%s/" % (subnet_id), method=requests.delete)

    ## Address

    def address_get(self, address_id):
        """Get Information about a specific address

        Parameters:
        address_id: The address identifier
        """
        return self.__query("/addresses/%s/" % (address_id))

    def address_get_ping(self, address_id):
        """Get ping status of specific address

        Parameters:
        address_id: The address identifier
        """
        return self.__query("/addresses/%s/ping/" % (address_id))

    def address_search(self, address):
        """Search for a specific address

        Parameters:
        address: The address identifier either the ID or address
        """
        return self.__query("/addresses/search/%s/" % (address))

    def address_search_hostname(self, hostname):
        """Search for all IPs with specified hostname

        Parameters:
        hostname: the hostname to search for
        """
        return self.__query("/addresses/search_hostname/%s/" % (hostname))

    def address_first_free(self, subnet_id):
        """Get first free IP address in subnet

        Parameters:
        subnet_id: The subnet identifier
        """
        return self.__query("/addresses/first_free/%s/" % (subnet_id))
    
    def address_get_custom_fields(self):
        """Get all address custom fields
        """
        return self.__query("/addresses/custom_fields/")

    def address_get_tag_all(self):
        """Get all address tags
        """
        return self.__query("/addresses/tags/")

    def address_get_tag(self, tag_id):
        """Get specific address tag

        Parameters:
        tag_id: the tag identifier
        """
        return self.__query("/addresses/tags/%s/" % (tag_id))

    def address_get_tag_addresses(self, tag_id):
        """Get addresses for specific tag

        Parameters:
        tag_id: the tag identifier
        """
        return self.__query("/addresses/tags/%s/addresses/" % (tag_id))

    def address_update(self, ip, hostname=None, description=None, is_gateway=None, mac=None):
        """Update address informations"""
        orgdata = self.address_search(ip)[0]
        data = {}
        if hostname != None: data["hostname"] = hostname
        if description != None: data["description"] = description
        if is_gateway != None: data["is_gateway"] = is_gateway
        if mac != None: data["mac"] = mac
        return self.__query("/addresses/%s/"%orgdata['id'], method=requests.patch, data=data)

    def address_create(self, ip, subnetId, hostname, description="", is_gateway=0, mac=""):
        """Create new address

        Parameters:
        number: address number
        name: short name
        description: description"""
        data = {
            "ip":ip,
            "subnetId":subnetId,
            "hostname":hostname,
            "description":description,
            "is_gateway":is_gateway,
            "mac": mac,
        }
        return self.__query("/addresses/", data=data)

    def address_delete(self, address_id):
        """Delete an address

        Parameters:
        address_id: the address identifier
        """
        return self.__query("/addresses/%s/" % (address_id), method=requests.delete)

    def address_delete_by_ip(self, ip_addr, subnet_id):
        """Delete an address in specific subnet

        Parameters:
        ip_addr: IP address in dotted decimal format
        subnet_id: the subnet identifier
        """
        return self.__query("/addresses/%s/%s/" % (ip_addr, subnet_id), method=requests.delete)

    ## VLAN

    def vlan_get_all(self):
        """Get all vlans
        """
        return self.__query("/vlans/")

    def vlan_get(self, vlan_id):
        """Get Information about a specific vlan

        Parameters:
        vlan_id: The vlan identifier either the ID or cidr
        """
        return self.__query("/vlans/%s/" % (vlan_id))

    '''
    def vlan_get_id(self, vlan_id):
        """vlan_get_id
        search for the ID of a vlan.

        Parameters:
        vlan: The vlan to search for
        """
        return self.__query("/vlans/search/%s/" % (vlan_id))[0]['id']
    '''

    def vlan_search(self, vlan_id):
        """vlan_get_id
        search for the ID of a vlan.

        Parameters:
        vlan: The vlan to search for
        """
        return self.__query("/vlans/search/%s/" % (vlan_id))

    def vlan_subnets(self, vlan_id):
        """Get vlan subnets

        Parameters:
        vlan_id: The vlan identifier
        """
        return self.__query("/vlans/%s/subnets/" % (vlan_id))

    def vlan_custom_fields(self):
        """Get all vlan custom fields
        """
        return self.__query("/vlans/custom_fields/")

    def vlan_subnets_section(self, vlan_id, section_id):
        """Get vlan subnets in specific section

        Parameters:
        vlan_id: The vlan identifier
        section_id: The section identifier
        """
        return self.__query("/vlans/%s/subnets/%s/" % (vlan_id, section_id))

    def vlan_create(self, number, name, description=""):
        """Create new vlan

        Parameters:
        number: vlan number
        name: short name
        description: description
        """
        data={
            'number' : number,
            'name' : name,
            'description' : description,
        }
        return self.__query("/vlans/", data=data)

    def vlan_delete(self, vlan_id):
        """Delete a vlan

        Parameters:
        vlan_id = vlan name or id.
        """
        return self.__query("/vlans/%s/" % (vlan_id), method=requests.delete)

    ## L2 Domains

    def l2domains_get_all(self):
        """Get all l2domains
        """
        return self.__query("/l2domains/")

    def l2domains_get(self, l2domain_id):
        """Get a specific l2domain

        Parameters:
        l2domain_id: the l2domain identifier
        """
        return self.__query("/l2domains/%s/" % (l2domain_id))

    def l2domains_get_vlans(self, l2domain_id):
        """Get vlans for a specific l2domain

        Parameters:
        l2domain_id: the l2domain identifier
        """
        return self.__query("/l2domains/%s/vlans/" % (l2domain_id))

    def l2domains_get_custom_fields(self):
        """Get all l2domain custom fields
        """
        return self.__query("/l2domains/custom_fields/")

    def l2domains_create(self, name, description=None):
        """Create an l2domain

        Parameters:
        name: the name of the l2domain
        description: description of the l2domain
        """
        data = {
            "name":name,
            "description":description
        }
        return self.__query("/l2domains/", data=data)

    def l2domains_delete(self, l2domain_id):
        """Delete an l2domain

        Parameters:
        l2domain_id: the l2domain identifier
        """
        return self.__query("/l2domains/%s/" % (l2domain_id), method=requests.delete)

    ## VRF

    def vrf_get_all(self):
        """Get all vrfs
        """
        return self.__query("/vrf/")

    def vrf_get(self, vrf_id):
        """Get a specific vrf

        Parameters:
        vrf_id: the vrf identifier
        """
        return self.__query("/vrf/%s/" % (vrf_id))

    def vrf_get_subnets(self, vrf_id):
        """Get subnets for a specific vrf

        Parameters:
        vrf_id: the vrf identifier
        """
        return self.__query("/vrf/%s/subnets/" % (vrf_id))

    def vrf_get_custom_fields(self):
        """Get all vrf custom fields
        """
        return self.__query("/vrf/custom_fields/")

    def vrf_create(self, name, description=None,rd=None,sections=None):
        """Create a vrf

        Parameters:
        name: the name of the vrf
        description: description of the vrf
        rd: vrf route distinguisher
        sections: sections in which to display vrf, blank shows in all
        """
        data = {
            "name":name,
            "description":description,
            "rd":rd,
            "sections":sections
        }
        return self.__query("/vrf/", data=data)

    def vrf_delete(self, vrf_id):
        """Delete a vrf

        Parameters:
        vrf_id: the vrf identifier
        """
        return self.__query("/vrfs/%s/" % (vrf_id), method=requests.delete)

    ## Devices

    def devices_get_all(self):
        """Get a list of all devices
        """
        return self.__query("/devices/")

    def devices_get(self, device_id):
        """Get Information about a specific device

        Parameters:
        device_id: The device identifier
        """
        return self.__query("/devices/%s/" % (device_id))

    def devices_get_subnets(self, device_id):
        """Get all subnets within device

        Parameters:
        device_id: The device identifier
        """
        return self.__query("/devices/%s/subnets/" % (device_id))

    def devices_get_addresses(self, device_id):
        """Get all addresses within device

        Parameters:
        device_id: The device identifier
        """
        return self.__query("/devices/%s/addresses/" % (device_id))

    def devices_search(self, search_string):
        """Get all devices with provided string anywhere in any field

        Parameters:
        search_string: The string to search for
        """
        return self.__query("/devices/search/%s/" % (search_string))

    def devices_create(self, hostname, sections=None, location=None, ip_addr=None, rack=None,
            rack_start=None, rack_size=None):
        """Create new device

        Parameters:
        hostname: the name of the device
        description: description of the device
        sections: string of section IDs, in numeric ID form, separated by semicolon
        location: location where the device exists, in numeric ID form
        ip_addr: IP address of the device
        rack: rack where the device exists, in numeric ID form
        rack_start: location of the device in the specified rack
        rack_size: size of the device, in rack U
        """
        data = {
            "hostname":hostname,
            "description":description,
            "sections":sections,
            "location":location,
            "ip_addr":ip_addr,
            "rack":rack,
            "rack_start":rack_start,
            "rack_size":rack_size
        }
        return self.__query("/devices/", data=data)

    def devices_delete(self, device_id):
        """Delete a device

        Parameters:
        device_id: the id of the device
        """
        return self.__query("/devices/%s/" % (device_id), method=requests.delete)
    
    # Prefixes

    def prefix_get_subnet_all(self, customer_type):
        """Get all subnets available as part of 'customer_type'

        Parameters:
        cutomer_type
        """
        return self.__query("/prefix/%s/" % (customer_type))

    def prefix_get_subnet_version(self, customer_type, version):
        """Get all subnets available as part of 'customer_type', specific to either IPv4 or IPv6

        Parameters:
        cutomer_type
        version: 4 or 6
        """
        return self.__query("/prefix/%s/%s/" % (customer_type, version))

    def prefix_get_address_all(self, customer_type):
        """Get all addresses available as part of 'customer_type'

        Parameters:
        cutomer_type
        """
        return self.__query("/prefix/%s/address/" % (customer_type))

    def prefix_get_address_version(self, customer_type, version):
        """Get all address available as part of 'customer_type', specific to either IPv4 or IPv6

        Parameters:
        cutomer_type
        version: 4 or 6
        """
        return self.__query("/prefix/%s/address/%s/" % (customer_type, version))


    def prefix_get_avail_subnet(self, customer_type, version, mask):
        """Get first available subnet of version 'version' and mask 'mask'

        Parameters:
        cutomer_type
        version: 4 or 6
        mask: the subnet prefix length
        """
        return self.__query("/prefix/%s/%s/%s/" % (customer_type, version, mask))
    
    def prefix_get_avail_address(self, customer_type, version):
        """Get first available address of version 'version' 

        Parameters:
        cutomer_type
        version: 4 or 6
        """
        return self.__query("/prefix/%s/%s/address/" % (customer_type, version))


    def prefix_create_subnet(self, customer_type, version, mask, description=None):
        """Create first available subnet of version 'version' and mask 'mask'

        Parameters:
        cutomer_type
        version: 4 or 6
        mask: the subnet prefix length
        description: the description of the subnet
        """
        data={
            'description' : description
        }
        return self.__query("/prefix/%s/%s/%s/" % (customer_type, version, mask), data=data)
    
    def prefix_create_address(self, customer_type, version, description=None):
        """Create first available address of version 'version' 

        Parameters:
        cutomer_type
        version: 4 or 6
        """
        data={
            'description' : description
        }
        return self.__query("/prefix/%s/%s/address/" % (customer_type, version), data=data)
