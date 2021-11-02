import json
import logging
import re
from typing import Optional

from bs4 import BeautifulSoup
from gobits import Gobits
from google.cloud import pubsub_v1

from config import (
    SENDER_WHITELIST,
    TYPE_FIELD,
    ALLOWED_TYPES,
    FIELDS,
    TOPIC_NAME,
    TOPIC_PROJECT_ID
)


HEADER_REGEX = re.compile(r"([^\n:]+):\s*<<?([^>]*)>>?")
TICKET_NUMBER_REGEX = re.compile(r"^[^[]+\[(Ticket#[^]]+)]")

logging.basicConfig(level=logging.INFO)


class EmailProcessor(object):

    def process(self, payload):
        mail = payload["email"]
        if self.process_mail(mail) is False:
            logging.info("Message not processed")
        else:
            logging.info("Message is processed")

    def _parse_structured_mail(self, html_text_raw: str) -> dict:
        """
        Extracts information from HTML e-mail content in structured e-mail format.

        :param html_text_raw: Raw HTML contents from e-mail.
        :type html_text_raw: str
        :return: Field-value pairs extracted from the provided HTML.
        :rtype: str
        """
        html_content = BeautifulSoup(html_text_raw, "html.parser")
        html_text_rendered = html_content.get_text()

        headers = self._get_field_value_pairs(html_text_rendered)
        table = self._get_html_table_contents(html_content)

        # Merging data, and transforming field names.
        variables = self._merge_dictionaries(headers, table)
        variables = {field.lower().replace(" ", "_"): value for field, value in variables.items()}

        return variables

    def _get_field_value_pairs(self, string: str) -> dict:
        """
        Extracts field-value pairs from string.

        Example of field-value structure:
        field: <<value>>
        multi_line: <<Line 1
        Line 2
        Line 3>>

        :param string: Plain text containing field-value pairs
        :type string: str
        :return: A dictionary with all field-value pairs.
        :rtype: dict
        """
        values = dict()
        for match in HEADER_REGEX.findall(string):
            field, value = match
            if not field:
                continue

            field = self._sanitise_string(field)
            value = self._sanitise_string(value)

            values[field] = value

        return values

    def _get_html_table_contents(self, html_content: BeautifulSoup) -> dict:
        """
        Extracts field-value pairs from the first table in the HTML content.

        This table must have 2 columns, the first one being the field, the second the value.

        Example of accepted HTML table:
        <table>
            <tbody>
                <tr>
                    <td>field</td>
                    <td>value</td>
                </tr>
            </tbody>
        </table>

        :param html_content: The HTML content to extract the table contents from.
        :type html_content: BeautifulSoup
        :return: A dictionary containing field-value pairs found in the table.
        :rtype: dict
        """
        values = dict()
        rows = [table_data.text for table_data in html_content.table.find_all("td")]
        data_count = len(rows)

        if data_count % 2:
            logging.error("The table must have 2 columns.")
            return values

        for i in range(0, data_count, 2):
            field, value = rows[i:i + 2]
            if not field:
                continue

            if field[-1] == ":":
                field = field[:-1]

            field = self._sanitise_string(field)
            value = self._sanitise_string(value)

            values[field] = value

        return values

    @staticmethod
    def _merge_dictionaries(dictionary: dict, other: dict) -> dict:
        """
        Merges 2 dictionaries.

        When a field already exists in the dictionary, the fields name will change to "field_{counter}"
        until an available field name is found.

        :param dictionary: The dictionary to merge into.
        :type dictionary: dict
        :param other: The dictionary to merge.
        :type other: dict
        :return: A merged dictionary.
        :rtype: dict
        """
        for field, value in other.items():
            counter = 1
            alt_field = field
            while alt_field in dictionary:
                alt_field = f"{field}_{counter}"
                counter += 1

            dictionary[alt_field] = value

        return dictionary

    @staticmethod
    def _sanitise_string(string: str) -> str:
        """
        Sanitises string coming from HTML, to be used in a dictionary.

        :param string: The string to sanitise.
        :type string: str
        :return: The sanitised string.
        :rtype: str
        """
        if not string:
            return str()

        # Removing HTML &nbsp; unicode characters.
        string = string.replace(u"\xa0", u" ")
        string = string.strip()

        return string

    def process_mail(self, mail) -> bool:
        mail_sender = mail["sender"].lower()

        if mail_sender not in SENDER_WHITELIST:
            date = mail.get("received_on", "")
            logging.error(
                f"E-mail received on {str(date)} was not send by a whitelisted e-mail address ({mail_sender})."
            )
            return False

        html_content = mail["body"]
        structured_mail_variables = self._parse_structured_mail(html_content)

        # Checking if all configured fields are present.
        all_fields_present = True
        for field in FIELDS:
            if field not in structured_mail_variables:
                all_fields_present = False
                logging.error(f"Field '{field}' was not found in e-mail data.")

        if not all_fields_present:
            return False

        mail_type = structured_mail_variables[TYPE_FIELD]
        if mail_type not in ALLOWED_TYPES:
            logging.error(f"'{mail_type}' is not an allowed type.")
            return False

        structured_mail_variables["id"] = self._generate_id(mail, mail_type)

        metadata = Gobits()
        return self._publish_to_topic(structured_mail_variables, metadata)

    @staticmethod
    def _generate_id(mail: dict, message_type: str) -> Optional[str]:
        """
        Generates an id for the specified e-mail.

        :param mail: The e-mail object.
        :type mail: dict
        :param message_type: Type of this e-mails message.
        :type message_type: str
        :return: The generated id for the e-mail.
        :rtype: str|None
        """
        received_on = mail["received_on"].split("+")[0].replace(":", "-")
        subject = mail["subject"]

        match = TICKET_NUMBER_REGEX.match(subject)
        if not match:
            logging.error("No ticket number found in e-mail subject.")
            return None

        ticket_number = match.group(1)

        return f"{message_type}_{ticket_number}_{received_on}"

    @staticmethod
    def _publish_to_topic(message, gobits) -> bool:
        pubsub_message = {"gobits": [gobits.to_json()], "parsed_email": message}
        try:
            # Publish to topic
            publisher = pubsub_v1.PublisherClient()
            topic_path = "projects/{}/topics/{}".format(
                TOPIC_PROJECT_ID, TOPIC_NAME
            )
            future = publisher.publish(
                topic_path, bytes(json.dumps(pubsub_message).encode("utf-8"))
            )
            future.add_done_callback(
                lambda x: logging.debug(f"Published email with ID {message['id']}")
            )
            logging.info(f"Publishing email with ID {message['id']}")
            return True
        except Exception as e:
            logging.exception(
                "Unable to publish parsed email to topic because of {}".format(e)
            )
        return False
