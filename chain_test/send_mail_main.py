import logging
from mailprocessor import MailProcessor
import sys
import argparse

parser = MailProcessor()

logging.basicConfig(level=logging.INFO)


def handler(mail_template):
    # Extract subscription from subscription string
    try:
        processed = parser.send_mails(mail_template)
        if processed is False:
            logging.info("E-Mail was not send")
            sys.exit(1)
        else:
            logging.info("E-Mail was send")

    except Exception as e:
        logging.info('Test to send email failed')
        logging.debug(e)
        raise e

    # Returning any 2xx status indicates successful receipt of the message.
    # 204: no content, delivery successfull, no further actions needed
    return 'OK', 204


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-t', '--mail-template', required=True)
    args = argparser.parse_args()
    mail_template = args.mail_template
    handler(mail_template)
