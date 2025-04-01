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
import time
import json
from datetime import datetime, timedelta

from clientparser.config import Config
from clientparser.database import initialize_and_create_tables, session_scope, DHCPModel, DNSModel, DBException
from concurrent.futures import ThreadPoolExecutor


__all__ = ["ClientParser"]


class ClientParser:

    config = Config()

    def _get_dhcp_data(self, verbose: bool) -> None:
        """Get the DHCP data and save it to the database and/or an output file."""
        
        # Run DHCP commands for all scopes concurrently
        with ThreadPoolExecutor() as executor:
            futures = []
            for scope in self.config.scopes:
                # Define the netsh command
                netsh_command = f"netsh dhcp server \\\\{self.config.dhcp_server} scope {scope} show clients 1"
                # Submit the command to the executor
                futures.append(executor.submit(subprocess.run, netsh_command, shell=True, capture_output=True, text=True))

            for future, scope in zip(futures, self.config.scopes):
                try:
                    current_scope = future.result()
                    if verbose:
                        print(f"Processing DHCP scope: {scope}")
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
                except Exception as e:
                    raise RuntimeError(f"Error processing scope {scope}: {e}")

    def _get_dns_forward_data(self, verbose: bool) -> None:
        """Gets the DNS forward lookup zone data and saves it to the database."""
        
        if verbose:
            print(f"Processing DNS forward lookup zone: {self.config.dns_zone}")

        # Define the PowerShell command to get the DNS records
        forward_lookup_zone_powershell_command = f"""
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
        dns_records = subprocess.run(["powershell", "-Command", forward_lookup_zone_powershell_command], capture_output=True, text=True)
        
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

    def _get_dns_reverse_data(self, verbose: bool) -> None:
        """Gets the DNS reverse lookup zone data and saves it to the database."""
        
        # Run PowerShell commands for all reverse lookup zones concurrently
        with ThreadPoolExecutor() as executor:
            futures = []
            for zone in self.config.dns_reverse_zones:
                # Define the PowerShell command to get the reverse lookup zone
                reverse_lookup_zones_powershell_command = f"""
                    $Report = [System.Collections.Generic.List[Object]]::new()
                    $zoneName = '{zone}'
                    $serverName = '{self.config.dns_server}'
                    $zoneInfo = Get-DnsServerResourceRecord -ComputerName $serverName -ZoneName $zoneName
                    foreach ($info in $zoneInfo) {{

                    $recordData = switch ($info.RecordType) {{
                        'PTR'       {{ $info.RecordData.PtrDomainName }}
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

                # Submit the PowerShell command to the executor
                futures.append(executor.submit(subprocess.run, ["powershell", "-Command", reverse_lookup_zones_powershell_command], capture_output=True, text=True))

            for future, zone in zip(futures, self.config.dns_reverse_zones):
                try:
                    reverse_dns_records = future.result()
                    if verbose:
                        print(f"Processing reverse lookup zone: {zone}")
                    # Parse the JSON output from PowerShell
                    for record in json.loads(reverse_dns_records.stdout):
                        
                        name = record.get("Name", "").strip()
                        hostname = record.get("Hostname", "").strip()
                        record_type = record.get("Type", "").strip()
                        data = str(record.get("Data", "")).strip()
                        timestamp = datetime.now()

                        # Reverse the IP address dynamically
                        reversed_ip = ".".join(reversed(zone[:-13].split(".")))

                        # Remove the trailing forward zone name from the data
                        if data.lower().endswith(f".{self.config.dns_zone.lower()}."):
                            data = data[:-len(self.config.dns_zone) - 2]

                        # Create a new DNS entry
                        new_entry = DNSModel(
                            name=name,
                            hostname=data,
                            record_type=record_type,
                            data=f"{reversed_ip}.{hostname}",
                            timestamp=timestamp
                        )

                        # Add the new entry to the database
                        with session_scope() as session:
                            try:
                                session.add(new_entry)
                            except Exception as e:
                                raise DBException(f"Error adding {name} to the database: {e}")
                except Exception as e:
                    raise RuntimeError(f"Error processing zone {zone}: {e}")
                

    def _get_data(self, verbose: bool) -> None:
        """Get the DHCP and DNS data and save it to the database."""
        # Set the start time
        start_time = datetime.now()
        # Initialize the database connection and create tables
        initialize_and_create_tables()

        # Run DHCP and DNS data collection concurrently
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self._get_dhcp_data, verbose),
                executor.submit(self._get_dns_forward_data, verbose),
                executor.submit(self._get_dns_reverse_data, verbose)
            ]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    raise RuntimeError(f"Error occurred during execution: {e}")
        
        if verbose:
            # Print the total runtime
            print(f"Total runtime: {datetime.now() - start_time}")

    def run(self, verbose: bool, interval: int) -> None:
        """Run the Client Parser application loop."""

        # Create a loop that runs the application every 5 minutes
        is_last_run = False
        last_runtime: datetime = datetime.now()

        while not is_last_run:

            # Check if the interval is set
            if interval == 0:
                is_last_run = True
                # Get the data
                self._get_data(verbose=verbose)
            
            elif (datetime.now() - last_runtime).seconds >= interval:
                last_runtime = datetime.now()
                # Get the data
                self._get_data(verbose=verbose)

                # Update the last runtime
                last_runtime = datetime.now()

            # Display the next runtime
            if interval != 0:
                next_runtime = last_runtime + timedelta(seconds=interval)

                if verbose:
                    print(f"Next run in {(next_runtime - datetime.now()).seconds} seconds")

                # Sleep for a second
                time.sleep(1)
