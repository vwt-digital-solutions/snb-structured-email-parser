from config import TOPIC_PROJECT_ID, TOPIC_NAME, HTML_TEMPLATE_PATHS, \
                   TEMPLATE_PATH_FIELD, RECIPIENT, SENDER
import logging
import json
import os
from jinja2 import Template
import datetime
from gobits import Gobits
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO)


class MessageProcessor(object):

    def __init__(self):
        self.data_selector = os.environ.get('DATA_SELECTOR', 'Required environment variable DATA_SELECTOR is missing')
        self.topic_project_id = TOPIC_PROJECT_ID
        self.topic_name = TOPIC_NAME
        self.html_template_field = TEMPLATE_PATH_FIELD
        self.html_template_paths = HTML_TEMPLATE_PATHS
        self.recipient = RECIPIENT
        self.sender = SENDER

    def process(self, payload):
        # Get message
        message = payload[self.data_selector]
        # Message to HTML body
        html_body, subject = self.message_to_html(message)
        if not html_body or not subject:
            logging.error("Message was not processed")
            return False
        # Make topic message
        topic_message = self.make_topic_msg(html_body, subject)
        # Make gobits
        gobits = Gobits()
        # Send message to topic
        return_bool = self.publish_to_topic(subject, topic_message, gobits)
        if return_bool is False:
            logging.error("Message was not processed")
            return False
        else:
            logging.info("Message was processed")
        return True

    def make_topic_msg(self, body, subject):
        now = datetime.datetime.now()
        now_iso = now.isoformat()
        message = {
            "sent_on": now_iso,
            "received_on": "",
            "sender": self.sender,
            "recipient": self.recipient,
            "subject": subject,
            "body": body,
            "attachments": []
        }
        return message

    def message_to_html(self, message):
        if not self.html_template_paths:
            logging.error("HTML template path is not defined in config")
            return None, None
        message_after_root = {}
        count = 0
        # Get part of message after the root
        for after_root in message:
            if isinstance(message[after_root], dict):
                message_after_root = message[after_root]
            count = count + 1
        if count > 1:
            logging.error("The message contains multiple roots")
            return None, None
        if not message_after_root:
            logging.error("The message does not contain a root")
            return None, None
        # Get message field
        temp_msg_field = message_after_root.get(self.html_template_field)
        if not temp_msg_field:
            logging.error("Could not get right message field to get template")
            return None, None
        # Get the right template
        temp_info = self.html_template_paths.get(temp_msg_field)
        template_path = temp_info.get('template_path')
        if not template_path:
            logging.error(f"Template paths in config do not have field {temp_msg_field}")
            return None, None
        template_args = temp_info.get('template_args')
        kwargs = {}
        for arg_field in template_args:
            # Get value
            arg_value = ""
            arg_field_values = template_args[arg_field]
            for arg_field_value in arg_field_values:
                # Check if value is MESSAGE_FIELD
                if arg_field_values[arg_field_value] == "MESSAGE_FIELD":
                    # Get value from message
                    arg_value = message_after_root.get(arg_field_value)
                kwargs.update({arg_field: arg_value})
        with open(template_path) as file_:
            template = Template(file_.read())
        body = template.render(kwargs)
        mail_subject = temp_info.get('mail_subject')
        if not mail_subject:
            logging.error(f"Field mail_subject could not be found in field {temp_msg_field}")
            return None, None
        # Get subject
        subject = ""
        for field in mail_subject:
            to_add = ""
            if mail_subject[field] == "HARDCODED":
                to_add = field
            elif mail_subject[field] == "MESSAGE_FIELD":
                subject_msg_field = message_after_root.get(field)
                # Check if subject field is found
                if not subject_msg_field:
                    logging.error(f"Field {field} could not be found in message")
                    return None, None
                to_add = subject_msg_field
            # If subject is not empty
            if subject:
                subject = f"{subject} {to_add}"
            else:
                subject = to_add
        return body, subject

    def publish_to_topic(self, subject, message, gobits):
        msg = {
            "gobits": [gobits.to_json()],
            "email": message
        }
        try:
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = "projects/{}/topics/{}".format(
                self.topic_project_id, self.topic_name)
            future = publisher.publish(
                topic_path, bytes(json.dumps(msg).encode('utf-8')))
            future.add_done_callback(
                lambda x: logging.debug('Published to export email with subject {}'.format(subject))
            )
            return True
        except Exception as e:
            logging.exception('Unable to publish parsed email ' +
                              'to topic because of {}'.format(e))
        return False
