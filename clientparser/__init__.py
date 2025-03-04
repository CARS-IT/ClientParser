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
from datetime import datetime

from clientparser.config import Config
from clientparser.database import initialize_and_create_tables, session_scope, DHCPModel, DBException


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
                    lease_parts = re.split(r"-(N|U)-", lease, maxsplit=1)

                    if len(lease_parts) > 1:
                        small_lease_parts = lease_parts[0].split("-")

                        # Get the IP address, MAC address, lease status, hostname, and timestamp
                        ip_address = small_lease_parts[0].strip()
                        mac_address = ":".join(part.strip().upper() for part in small_lease_parts[2:-1])

                        # Check if the MAC address is longer than the normal length (17 characters)
                        if len(mac_address) > 17:
                            mac_address = mac_address + ":XX"

                        lease_status = small_lease_parts[-1].strip()
                        hostname = lease_parts[2].strip().split(".")[0].lower()s
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
                                timestamp=timestamp,
                            )

                        # Add the new entry to the database
                        with session_scope() as session:
                            try:
                                session.add(new_entry)
                            except Exception as e:
                                raise DBException(f"Error adding {ip_address} to the database: {e}")

    def run(self) -> None:
        """Run the Client Parser application."""
        # Initialize the database connection and create tables
        initialize_and_create_tables()
        # Get the DHCP data
        self._get_dhcp_data()
