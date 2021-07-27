import json
import logging

from bs4 import BeautifulSoup
from config import (ID, NEEDED_ID_VALUE, REQUIRED_FIELDS, SENDERS, TOPIC_NAME,
                    TOPIC_PROJECT_ID)
from gobits import Gobits
from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO)


class EmailProcessor(object):
    def __init__(self):
        self.senders = SENDERS
        self.required_fields = REQUIRED_FIELDS
        self.topic_project_id = TOPIC_PROJECT_ID
        self.topic_name = TOPIC_NAME
        self.parsed_email_id = "".join(ID)
        self.id = ID
        self.needed_id_value = NEEDED_ID_VALUE

    def process(self, payload):
        mail = payload["email"]
        if self.process_mail(mail) is False:
            logging.info("Message not processed")
        else:
            logging.info("Message is processed")

    def process_mail(self, mail):
        mail_sender = mail["sender"]
        date = ""
        if "received_on" in mail:
            date = mail["received_on"]
        if mail_sender not in self.senders:
            if date:
                logging.info(
                    "Mail received on {} was not send by the right e-mail address".format(
                        date
                    )
                )
                return False
            else:
                logging.info("Mail received was not send by the right e-mail address")
                return False
        html_content = mail["body"]
        # Check if code contains "<table>", "<tr>" and "<td>" tags
        if (
            "<table>" not in html_content
            or "<tr>" not in html_content
            or "<td>" not in html_content
        ):
            logging.info("Required tags cannot be found in HTML body")
            return False
        # Get list from above table
        html_above_table = html_content.split("<table>")[0]
        html_above_table_list = self.get_part_above_table_list(html_above_table)
        if not html_above_table_list:
            return False
        # Add the fields from above the table of the HTML to the message
        new_message = self.add_fields_not_table(html_above_table_list)
        # HTML to parse-able content
        parsed_html = BeautifulSoup(html_content, "html.parser")
        # Add fields from the table in the HTML to the message
        new_message = self.add_fields_table(parsed_html, new_message)
        # Make sure that every required field is added
        new_message = self.required_fields_check(new_message)
        if not new_message:
            return False
        # Check if ID is correct
        if self.id_check(new_message) is False:
            return False
        # Add an ID
        new_message = self.add_id(mail, new_message)
        if not new_message:
            return False
        metadata = Gobits()
        return_bool_publish_topic = self.publish_to_topic(new_message, metadata)
        if not return_bool_publish_topic:
            return False
        return True

    def get_part_above_table_list(self, html_above_table):
        # Check if the part is not empty
        if not html_above_table:
            logging.info("HTML body does not have the required structure")
            return []
        html_above_table_list = html_above_table.split("\n")
        # If the length is 1
        if len(html_above_table_list) == 1:
            # Try to split on \\n
            html_above_table_list = html_above_table.split("\\n")
        # If the length is empty
        if not html_above_table_list:
            logging.error("There should be apart above the table in the email")
            return []
        return html_above_table_list

    def add_fields_not_table(self, html_above_table_list):
        # The new json to be send
        new_message = {}
        # For every line in the part above the table
        for line in html_above_table_list:
            field = ""
            value = ""
            # If the line contains information
            if line:
                # Remove '&nbsp;' from line
                if "&nbsp;" in line:
                    line = line.replace("&nbsp;", " ")
                # If line ends with '&lt;&lt;'
                if str(line).endswith("&lt;&lt; ") or str(line).endswith("&lt;&lt;"):
                    # Split the line on ': <<'
                    line_list = line.split(":")
                else:
                    # Split the line on ': <<'
                    line_list = line.split(": &lt;&lt;")
                # The first value of the line is the field
                field = line_list.pop(0)
                # Check if the field can be found in the required fields
                if field in self.required_fields:
                    # If there were also ':' in the value of the field,
                    # there are multiple list items after the first
                    # Combine them again
                    value = "".join(line_list)
            if value:
                # Remove '<<' and '>>'
                value = value.replace("&lt;&lt;", "")
                value = value.replace("&gt;&gt;", "")
                # Check if value still has a value
                if value:
                    #  If the first character is a whitespace, remove it
                    if value[0] == " ":
                        value = value.replace(" ", "", 1)
            if field:
                new_message = self.add_field(field, value, new_message)
        return new_message

    def add_fields_table(self, parsed_html, new_message):
        # Get table part
        table = parsed_html.table
        # Get values from the table
        lines = table.find_all("tr")
        for line in lines:
            # Split on tag 'td'
            td_list = line.find_all("td")
            field = None
            if len(td_list) > 0:
                # Field
                field = td_list[0].get_text()
                # Split field on ':' and get first value
                if ':' in field:
                    field = field.split(":")[0]
            # value
            value = ""
            if len(td_list) > 1:
                value = td_list[1].get_text()
            if field:
                new_message = self.add_field(field, value, new_message)
        return new_message

    def required_fields_check(self, new_message):
        added_field_count = 0
        for field in self.required_fields:
            field = field.replace(" ", "_")
            field = field.lower()
            if field not in new_message:
                dict_line = {field: ""}
                new_message.update(dict_line)
                added_field_count = added_field_count + 1
        # Check if added fields are not equal to all the fields
        if added_field_count is len(self.required_fields):
            logging.info("HTML body does not contain any of the required fields")
            return {}
        return new_message

    def id_check(self, new_message):
        id_value = ""
        for an_id in self.id:
            id_value = new_message.get(an_id, "")
        if not id_value:
            logging.info(f"ID {self.id} cannot be found in message")
            return False
        if id_value != self.needed_id_value:
            logging.info(
                f"ID {self.id} found in message does not have the right value defined in the config"
            )
            return False
        return True

    def add_id(self, mail, new_message):
        received_on_list = mail["received_on"].split("+")
        received_on = received_on_list[0]
        received_on = received_on.replace(":", "-")
        subject_mail = mail["subject"]
        ticket_nr = ""
        for ch in range(len(subject_mail)):
            if subject_mail[ch] == "[":
                while True:
                    if ch + 1 > len(subject_mail):
                        break
                    if subject_mail[ch + 1] == "]":
                        break
                    ch = ch + 1
                    ticket_nr = ticket_nr + subject_mail[ch]
        if "Ticket#" not in ticket_nr:
            logging.info("The ticket number cannot be found in the e-mail")
            return {}
        if not new_message[self.parsed_email_id]:
            logging.error(f"ID {self.parsed_email_id} is empty in message")
            return {}
        new_message.update(
            {
                "id": "{}_{}_{}".format(
                    new_message[self.parsed_email_id], ticket_nr, received_on
                )
            }
        )
        return new_message

    def add_field(self, field, value, message):
        if field in self.required_fields:
            field = field.replace(" ", "_")
            field = field.replace(":", "")
            field = field.lower()
            # Check if field can already be found in message
            if field in message:
                # If it is, add an integer next to the field until the field is not in the message already
                count = 1
                while True:
                    if field not in message:
                        break
                    field = f"{field}_{count}"
                    count = count + 1
            # Remove HTML whitespace code from value
            if "&amp;nbsp;" in value:
                value = value.replace("&amp;nbsp;", " ")
            if "&nbsp;" in value:
                value = value.replace("&nbsp;", " ")
            # Remove non breaking whitespace HTML code from value
            if "\u00a0" in value:
                value = value.replace("\u00a0", " ")
            dict_line = {field: value}
            message.update(dict_line)
        return message

    def publish_to_topic(self, message, gobits):
        date = ""
        if "received_on" in message:
            date = message["received_on"]
        msg = {"gobits": [gobits.to_json()], "parsed_email": message}
        try:
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = "projects/{}/topics/{}".format(
                self.topic_project_id, self.topic_name
            )
            future = publisher.publish(
                topic_path, bytes(json.dumps(msg).encode("utf-8"))
            )
            if date:
                future.add_done_callback(
                    lambda x: logging.debug(
                        "Published parsed email with date {}".format(date)
                    )
                )
            future.add_done_callback(lambda x: logging.debug("Published parsed email"))
            logging.info(f"Publishing email with ID {message['id']}")
            return True
        except Exception as e:
            logging.exception(
                "Unable to publish parsed email " + "to topic because of {}".format(e)
            )
        return False
