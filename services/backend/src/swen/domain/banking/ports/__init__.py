"""Port interfaces for banking operations.

These interfaces define what the domain needs from external banking systems.
Implementations (adapters) are provided in the infrastructure layer.
"""

from swen.domain.banking.ports.bank_connection_port import BankConnectionPort

__all__ = [
    "BankConnectionPort",
]
