#!/usr/bin/env python3
# ----------------------------------------------------------------------------------
# Project: ClientParser
# File: clientparser/__init__.py
# ----------------------------------------------------------------------------------
# Purpose:
# This is the main entry point for the Client Parser application.
# ----------------------------------------------------------------------------------
# Author: Christofanis Skordas
#
# Copyright (C) 2025 GSECARS, The University of Chicago, USA
# Copyright (C) 2025 NSF SEES, USA
# ----------------------------------------------------------------------------------

import subprocess
import re
import json
from datetime import datetime

from clientparser.config import Config
from clientparser.database import initialize_and_create_tables, session_scope, DHCPModel, DNSModel, DBException


__all__ = ["ClientParser"]


class ClientParser:

    config = Config()

    def _get_dhcp_data(self) -> None:
        """Get the DHCP data and save it to the database and/or an output file."""

        for scope in self.config.scopes:
            # Define the netsh command
            netsh_command = f"netsh dhcp server \\\\{self.config.dhcp_server} scope {scope} show clients 1"

            # Run the netsh command
            current_scope = subprocess.run(netsh_command, shell=True, capture_output=True, text=True)

            # Filter the DHCP export command
            for lease in current_scope.stdout.splitlines():
                if lease.startswith("1"):
                    # Split the lease into parts
                    lease_parts = re.split(r"-(N|U|D)-", lease, maxsplit=1)

                    if len(lease_parts) > 1:
                        small_lease_parts = lease_parts[0].split("-")

                        # Get the IP address, MAC address, lease status, hostname, and timestamp
                        ip_address = small_lease_parts[0].strip()
                        mac_address = ":".join(part.strip().upper() for part in small_lease_parts[2:-1])

                        # Check if the MAC address is longer than the normal length (17 characters)
                        if len(mac_address) > 17:
                            mac_address = mac_address + ":XX"

                        lease_status = small_lease_parts[-1].strip()
                        hostname = lease_parts[2].strip().split(".")[0].lower()
                        subnet = scope.split()[0]
                        timestamp = datetime.now()

                        # Get the model class based on the scope
                        model_class = next((model for model in DHCPModel.create_dhcp_models([scope]) if model.scope == scope), None,)

                        # Create a new entry
                        if model_class:
                            new_entry = model_class(
                                ip=ip_address,
                                mac_address=mac_address,
                                lease_status=lease_status,
                                hostname=hostname,
                                subnet=subnet,
                                timestamp=timestamp,
                            )

                        # Add the new entry to the database
                        with session_scope() as session:
                            try:
                                session.add(new_entry)
                            except Exception as e:
                                raise DBException(f"Error adding {ip_address} to the database: {e}")
                            
    def _get_dns_data(self) -> None:
        """Get the DNS data and save it to the database."""
        
        # Define the powershell command
        zone_name = "cars.aps.anl.gov"
        server_name = "cars1"

        powershell_command = f"""
            $Report = [System.Collections.Generic.List[Object]]::new()
            $zoneName = '{self.config.dns_zone}'
            $serverName = '{self.config.dns_server}'
            $zoneInfo = Get-DnsServerResourceRecord -ComputerName $serverName -ZoneName $zoneName
            foreach ($info in $zoneInfo) {{

            $recordData = switch ($info.RecordType) {{
                'A'         {{ $info.RecordData.IPv4Address.IPAddressToString }}
                'AAAA'      {{ $info.RecordData.IPv6Address.IPAddressToString }}
                'CNAME'     {{ $info.RecordData.HostNameAlias }}
                'MX'        {{ $info.RecordData.MailExchange }}
                'NS'        {{ $info.RecordData.NameServer }}
                'PTR'       {{ $info.RecordData.PtrDomainName }}
                'SRV'       {{ "$($info.RecordData.Target) $($info.RecordData.Port)" }}
                'TXT'       {{ -join $info.RecordData.DescriptiveText }}
                default     {{ $null }}
            }}

            $ReportLine = [PSCustomObject]@{{
                Name       = $zoneName
                Hostname   = $info.Hostname
                Type       = $info.RecordType
                Data       = $recordData
            }}
            $Report.Add($ReportLine)
            }}

            # Print the results in a table format
            $Report | ConvertTo-Json 
        """

        # Run the powershell command
        dns_records = subprocess.run(["powershell", "-Command", powershell_command], capture_output=True, text=True)

        # Parse the JSON output from PowerShell
        for record in json.loads(dns_records.stdout):
                
            name = record.get("Name", "").strip()
            hostname = record.get("Hostname", "").strip()
            record_type = record.get("Type", "").strip()
            data = str(record.get("Data", "")).strip()
            timestamp = datetime.now()

            # Create a new DNS entry
            new_entry = DNSModel(
                name=name,
                hostname=hostname,
                record_type=record_type,
                data=data,
                timestamp=timestamp
            )

            # Add the new entry to the database
            with session_scope() as session:
                try:
                    session.add(new_entry)
                except Exception as e:
                    raise DBException(f"Error adding {name} to the database: {e}")


    def run(self) -> None:
        """Run the Client Parser application."""
        # Initialize the database connection and create tables
        initialize_and_create_tables()
        # Get the DHCP data
        self._get_dhcp_data()
        # Get the DNS data
        self._get_dns_data()
