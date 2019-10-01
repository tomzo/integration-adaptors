import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def body_contains_message_id(body: str, message_id: str) -> bool:
    """
    Returns true if the SOAP MessageID section contains the message if provided
    :param body: the SOAP request as a string
    :param message_id: the message_id expected
    :return: true if message_id was found in the SOAP request
    """
    root_xml = ET.fromstring(body)
    element_matching_xpath = root_xml.find('.//wsa:MessageID', namespaces={'wsa': 'http://schemas.xmlsoap.org/ws/2004/08/addressing'})

    if element_matching_xpath is None:
        logger.log(logging.INFO, f'message id {message_id} not found')
        return False

    logger.log(logging.INFO, f'Element matching xpath found with value: {element_matching_xpath.text}')
    return f'uuid:{message_id}' == element_matching_xpath.text