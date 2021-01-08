from config import EMAIL_PROPERTIES, SENDER, REQUIRED_FIELDS, TOPIC_NAME, TOPIC_PROJECT_ID
import os
import logging
import json
import sys
from gobits import Gobits
from google.cloud import pubsub_v1
from bleach import Cleaner, sanitizer


class EmailProcessor(object):

    def __init__(self):
        self.meta = EMAIL_PROPERTIES[os.environ.get('DATA_SELECTOR', 'Required parameter is missing')]
        self.sender = SENDER
        self.required_fields = REQUIRED_FIELDS
        self.topic_project_id = TOPIC_PROJECT_ID
        self.topic_name = TOPIC_NAME

    def process(self, payload):
        mail = payload[os.environ.get('DATA_SELECTOR', 'Required parameter is missing')]
        mail_sender = mail["sender"]
        date = ""
        if "Datum" in mail:
            date = mail["Datum"]
        if mail_sender != self.sender:
            if date:
                logging.info("Mail received on {} was not send by the right e-mail address".format(date))
                sys.exit(0)
            else:
                logging.info("Mail received was not send by the right e-mail address")
                sys.exit(0)
        mail_body = mail["body"]
        # TODO: remove below #
        custom_tags = sanitizer.ALLOWED_TAGS + ['tr', 'td', 'table', 'tbody']
        html_content = self.parse_html_content(mail_body, tags=custom_tags)
        ######################
        html_content = html_content.replace('<table>', '')
        html_content = html_content.replace('</table>', '')
        html_content = html_content.replace('<tbody>', '')
        html_content = html_content.replace('</tbody>', '')
        html_content = html_content.replace('<td>', '')
        html_content = html_content.replace('</td>', '')
        html_content_lines = html_content.split("\n")
        # The new json to be send
        new_message = {}
        # For every line in the HTML message
        for li in range(len(html_content_lines)):
            line = html_content_lines[li]
            field = ""
            value = ""
            # Check if there's a ': <<' in the line
            if ": &lt;&lt;" in line:
                # Split the line on ":"
                line_list = line.split(':')
                field = line_list.pop(0)
                # Check if the field can be found in the required fields
                if field in self.required_fields:
                    # If there were also ':' in the value of the field,
                    # there are multiple list items after the first
                    # Combine them again
                    value = ''.join(line_list)
            # Else check if <tr> is in the line
            elif "<tr>" in line:
                # If it is, the next line is field
                if (li + 1) > len(html_content_lines):
                    logging.error("Something went wrong in parsing the email")
                    sys.exit(1)
                field = html_content_lines[li+1]
                # Replace ':' in field
                field = field.replace(':', '')
                # If field can be found in required field
                if field in self.required_fields:
                    # The value are the lines until a </tr> is found
                    value = ''
                    line_index = li + 2
                    next_line = html_content_lines[line_index]
                    while True:
                        if "</tr>" in next_line:
                            break
                        if value:
                            value = value + "\n"
                        value = value + html_content_lines[line_index]
                        line_index = line_index + 1
                        next_line = html_content_lines[line_index]
                    if line_index < len(html_content_lines):
                        li = line_index
            if value:
                # Remove '<<' and '>>'
                value = value.replace('&lt;&lt;', '')
                value = value.replace('&gt;&gt;', '')
                # If the first character is a whitespace, remove it
                if value[0] == " ":
                    value = value.replace(' ', '', 1)
            if field and field in self.required_fields:
                field = field.replace(' ', '_')
                dict_line = {
                    field: value
                }
                new_message.update(dict_line)
        # Check if every required field was added
        for field in self.required_fields:
            field = field.replace(' ', '_')
            if field not in new_message:
                dict_line = {
                    field: ""
                }
                new_message.update(dict_line)
        # TODO: Uncomment below
        # metadata = Gobits.from_request(request=payload)
        # TODO: remove below #
        metadata = Gobits()
        ######################
        return_bool_publish_topic = self.publish_to_topic(new_message, metadata)
        if not return_bool_publish_topic:
            sys.exit(1)

    def publish_to_topic(self, message, gobits):
        date = ""
        if "Datum" in message:
            date = message["Datum"]
        msg = {
            "gobits": [gobits.to_json()],
            "parsed_email": message
        }
        try:
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = "projects/{}/topics/{}".format(
                self.topic_project_id, self.topic_name)
            future = publisher.publish(
                topic_path, bytes(json.dumps(msg).encode('utf-8')))
            if date:
                future.add_done_callback(
                    lambda x: logging.debug('Published parsed email with date {}'.format(date))
                )
            future.add_done_callback(
                lambda x: logging.debug('Published parsed email')
            )
            return True
        except Exception as e:
            logging.exception('Unable to publish parsed email ' +
                              'to topic because of {}'.format(e))
        return False

    # TODO: remove function below
    def parse_html_content(self, html, **kwargs):
        if html is None:
            return None
        cleaner = Cleaner(**kwargs, strip=True)
        return cleaner.clean(html)
