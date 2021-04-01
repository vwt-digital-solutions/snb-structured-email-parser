import base64
import json
import logging

from config import DEBUG_LOGGING

from messageprocessor import MessageProcessor

parser = MessageProcessor()

logging.basicConfig(level=logging.INFO)


def log(debug_message, normal_message):
    if DEBUG_LOGGING:
        logging.info(debug_message)
    else:
        logging.info(normal_message)


def msg_to_html_body(request):
    # Extract data from request
    envelope = json.loads(request.data.decode("utf-8"))
    payload = base64.b64decode(envelope["message"]["data"])

    # Extract subscription from subscription string
    try:
        subscription = envelope["subscription"].split("/")[-1]
        log(
            f"Message received from {subscription} [{payload}]",
            f"Message received from {subscription}",
        )

        parser.process(json.loads(payload))

    except Exception as e:
        logging.info("Extract of subscription failed")
        logging.debug(e)
        raise e

    # Returning any 2xx status indicates successful receipt of the message.
    # 204: no content, delivery successfull, no further actions needed
    return "OK", 204
