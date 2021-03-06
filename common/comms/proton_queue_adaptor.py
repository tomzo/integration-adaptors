"""Module for Proton specific queue adaptor functionality. """
import json
from typing import Dict, Any

import proton.handlers
import proton.reactor
import tornado.ioloop

import comms.queue_adaptor
import utilities.integration_adaptors_logger as log
import utilities.message_utilities

logger = log.IntegrationAdaptorsLogger('PROTON_QUEUE')


class MessageSendingError(RuntimeError):
    """An error occurred whilst sending a message to the Message Queue"""
    pass


class EarlyDisconnectError(RuntimeError):
    """The connection to the Message Queue ended before sending of the message had been done."""
    pass


class ProtonQueueAdaptor(comms.queue_adaptor.QueueAdaptor):
    """Proton implementation of a queue adaptor."""

    def __init__(self, **kwargs) -> None:
        """
        Construct a Proton implementation of a :class:`QueueAdaptor <comms.queue_adaptor.QueueAdaptor>`.
        The kwargs provided should contain the following information:
          * host: The host of the Message Queue to be interacted with.
          * username: The username to use to connect to the Message Queue.
          * password The password to use to connect to the Message Queue.
        :param kwargs: The key word arguments required for this constructor.
        """
        super().__init__()
        self.host = kwargs.get('host')
        self.username = kwargs.get('username')
        self.password = kwargs.get('password')
        logger.info('000', 'Initialized proton queue adaptor for {host}', {'host': self.host})

    async def send_async(self, message: dict, properties: Dict[str, Any] = None) -> None:
        """Builds and asynchronously sends a message to the host defined when this adaptor was constructed. Raises an
        exception to indicate that the message could not be sent successfully.

        :param message: The message body to send. This will be serialised as JSON.
        :param properties: Optional application properties to send with the message.
        """
        logger.info('008', 'Sending message asynchronously.')
        payload = self.__construct_message(message, properties=properties)
        await tornado.ioloop.IOLoop.current() \
            .run_in_executor(executor=None, func=lambda: self.__send(payload))

    async def send_raw_async(self, message_body, content_type):
        logger.info('008', 'Sending raw message asynchronously.')
        message_id = utilities.message_utilities.MessageUtilities.get_uuid()
        logger.info('001', 'Constructing message with {id}', {'id': message_id })
        await tornado.ioloop.IOLoop.current() \
            .run_in_executor(executor=None, func=lambda: self.__send(proton.Message(id=message_id, content_type=content_type, body=message_body)))

    @staticmethod
    def __construct_message(message: dict, properties: Dict[str, Any] = None) -> proton.Message:
        """
        Build a message with a generated uuid, and specified message body.
        :param message: The message body to be wrapped.
        :param properties: Optional application properties to send with the message.
        :return: The Message in the correct format with generated uuid.
        """
        message_id = utilities.message_utilities.MessageUtilities.get_uuid()
        logger.info('001', 'Constructing message with {id} and {applicationProperties}',
                    {'id': message_id, 'applicationProperties': properties})
        return proton.Message(id=message_id, content_type='application/json', body=json.dumps(message),
                              properties=properties)

    def __send(self, message: proton.Message) -> None:
        """
        Performs a synchronous send of a message, to the host defined when this adaptor was constructed.
        :param message: The message to be sent.
        """
        proton.reactor.Container(ProtonMessagingHandler(self.host, self.username, self.password, message)).run()


class ProtonMessagingHandler(proton.handlers.MessagingHandler):
    """Implementation of a Proton MessagingHandler which will send a single message. Note that this class will raise
    an exception to indicate that a message could not be sent successfully."""

    def __init__(self, host: str, username: str, password: str, message: proton.Message) -> None:
        """
        Constructs a MessagingHandler which will send a specified message to a specified host.
        :param host: The host to send the message to.
        :param username: The username to login to the host with.
        :param password: The password to login to the host with.
        :param message: The message to be sent to the host.
        """
        super().__init__()
        self._host = host
        self._username = username
        self._password = password
        self._message = message
        self._sender = None
        self._sent = False

    def on_start(self, event: proton.Event) -> None:
        """Called when this messaging handler is started.

        :param event: The start event.
        """
        logger.info('002', 'Establishing connection to {host} for sending messages.', {'host': self._host})
        self._sender = event.container.create_sender(proton.Url(self._host, username=self._username,
                                                                password=self._password))

    def on_sendable(self, event: proton.Event) -> None:
        """Called when the link is ready for sending messages.

        :param event: The sendable event.
        """
        if event.sender.credit:
            if not self._sent:
                event.sender.send(self._message)
                logger.info('003', 'Message sent to {host}.', {'host': self._host})
                self._sent = True
        else:
            logger.error('004', 'Failed to send message as no available credit.')
            raise MessageSendingError()

    def on_accepted(self, event: proton.Event) -> None:
        """Called when the outgoing message is accepted by the remote peer.

        :param event: The accepted event.
        """
        logger.info('005', 'Message received by {host}.', {'host': self._host})
        event.connection.close()

    def on_disconnected(self, event: proton.Event) -> None:
        """Called when the socket is disconnected.

        :param event: The disconnect event.
        """
        logger.info('006', 'Disconnected from {host}.', {'host': self._host})
        if not self._sent:
            logger.error('010', 'Disconnected before message could be sent.')
            raise EarlyDisconnectError()

    def on_rejected(self, event: proton.Event) -> None:
        """Called when the outgoing message is rejected by the remote peer.

        :param event:
        :return:
        """
        logger.warning('007', 'Message rejected by {host}.', {'host': self._host})
        self._sent = False

    def on_transport_error(self, event: proton.Event) -> None:
        """Called when an error is encountered with the transport over which the AMQP connection is established.

        :param event: The transport error event.
        """
        logger.error('011', "There was an error with the transport used for the connection to {host}.",
                     {'host': self._host})
        super().on_transport_error(event)
        raise EarlyDisconnectError()

    def on_connection_error(self, event: proton.Event) -> None:
        """Called when the peer closes the connection with an error condition.

        :param event: The connection error event.
        """
        logger.error('012', "{host} closed the connection with an error. {remote_condition}",
                     {'host': self._host, 'remote_condition': event.context.remote_condition})
        super().on_connection_error(event)
        raise EarlyDisconnectError()

    def on_session_error(self, event: proton.Event) -> None:
        """Called when the peer closes the session with an error condition.

        :param event: The session error event.
        """
        logger.error('013', "{host} closed the session with an error. {remote_condition}",
                     {'host': self._host, 'remote_condition': event.context.remote_condition})
        super().on_session_error(event)
        raise EarlyDisconnectError()

    def on_link_error(self, event: proton.Event) -> None:
        """Called when the peer closes the link with an error condition.

        :param event: The link error event.
        """
        logger.error('014', "{host} closed the link with an error. {remote_condition}",
                     {'host': self._host, 'remote_condition': event.context.remote_condition})
        super().on_link_error(event)
        raise EarlyDisconnectError()
