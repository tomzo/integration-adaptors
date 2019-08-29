"""Module for generic queue adaptor functionality"""
import abc
from typing import Dict, Any


class QueueAdaptor(abc.ABC):
    """Interface for a message queue adaptor."""

    @abc.abstractmethod
    async def send_async(self, message: str, properties: Dict[str, Any] = None) -> None:
        """
        Sends a message which awaits using the async flow.
        :param message: The message content to send.
        :param properties: Optional additional properties to send with the message.
        """
        pass

    @abc.abstractmethod
    def send_sync(self, message: str, properties: Dict[str, Any] = None) -> None:
        """
        Sends a message and blocks waiting for the send to complete.
        :param message: The message content to send.
        :param properties: Optional additional properties to send with the message.
        """
        pass