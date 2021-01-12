from config import SENDER, ID, REQUIRED_FIELDS, TOPIC_NAME, TOPIC_PROJECT_ID
import logging
import json
import sys
from gobits import Gobits
from google.cloud import pubsub_v1
from bs4 import BeautifulSoup


class EmailProcessor(object):

    def __init__(self):
        self.sender = SENDER
        self.required_fields = REQUIRED_FIELDS
        self.topic_project_id = TOPIC_PROJECT_ID
        self.topic_name = TOPIC_NAME
        self.parsed_email_id = "".join(ID)

    def process(self, payload):
        mail = payload["email"]
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
        html_content = mail["body"]
        # Check if code contains "<table>", "<tr>" and "<td>" tags
        if "<table>" not in html_content or \
           "<tr>" not in html_content or \
           "<td>" not in html_content:
            logging.info("Required tags cannot be found in HTML body")
            sys.exit(0)
        # Get part before table
        html_above_table = html_content.split('<table>')[0]
        # Check if the part is not empty
        if not html_above_table:
            logging.info("HTML body does not have the required structure")
            sys.exit(0)
        html_above_table_list = html_above_table.split("\n")
        # The new json to be send
        new_message = {}
        # For every line in the part above the table
        for line in html_above_table_list:
            field = ""
            value = ""
            # If the line contains information
            if line:
                # Split the line on ': <<'
                line_list = line.split(": &lt;&lt;")
                # The first value of the line is the field
                field = line_list.pop(0)
                # Check if the field can be found in the required fields
                if field in self.required_fields:
                    # If there were also ':' in the value of the field,
                    # there are multiple list items after the first
                    # Combine them again
                    value = ''.join(line_list)
            if value:
                # Remove '<<' and '>>'
                value = value.replace('&lt;&lt;', '')
                value = value.replace('&gt;&gt;', '')
                # Check if value still has a value
                if value:
                    #  If the first character is a whitespace, remove it
                    if value[0] == " ":
                        value = value.replace(' ', '', 1)
            if field:
                new_message = self.add_field(field, value, new_message)
        # HTML to parse-able content
        parsed_html = BeautifulSoup(html_content, 'html.parser')
        # Get table part
        table = parsed_html.table
        # Get values from the table
        lines = table.find_all('tr')
        for line in lines:
            # Split on tag 'td'
            td_list = line.find_all('td')
            # Field
            field = td_list[0].get_text()
            # value
            value = td_list[1].get_text()
            if field:
                new_message = self.add_field(field, value, new_message)
        # Check if every required field was added
        for field in self.required_fields:
            field = field.replace(' ', '_')
            field = field.lower()
            if field not in new_message:
                dict_line = {
                    field: ""
                }
                new_message.update(dict_line)
        # Add an ID
        received_on_list = mail["received_on"].split("+")
        received_on = received_on_list[0]
        received_on = received_on.replace(':', '-')
        subject_mail = mail["subject"]
        ticket_nr = ""
        for ch in range(len(subject_mail)):
            if subject_mail[ch] == "[":
                while True:
                    if ch + 1 > len(subject_mail):
                        break
                    if subject_mail[ch+1] == "]":
                        break
                    ch = ch + 1
                    ticket_nr = ticket_nr + subject_mail[ch]
        if "Ticket#" not in ticket_nr:
            logging.error("The ticket number cannot be found in the e-mail")
        new_message.update({"id": "{}_{}_{}".format(new_message[self.parsed_email_id], ticket_nr, received_on)})
        # TODO: Uncomment below
        # metadata = Gobits.from_request(request=payload)
        # TODO: remove below #
        metadata = Gobits()
        ######################
        return_bool_publish_topic = self.publish_to_topic(new_message, metadata)
        if not return_bool_publish_topic:
            sys.exit(1)

    def add_field(self, field, value, message):
        if field in self.required_fields:
            field = field.replace(' ', '_')
            field = field.replace(':', '')
            field = field.lower()
            dict_line = {
                field: value
            }
            message.update(dict_line)
        return message

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
