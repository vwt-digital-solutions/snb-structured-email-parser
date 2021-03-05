import config
import logging
import base64
from apiclient import errors

import google.auth
import googleapiclient.discovery
from google.auth import iam
from google.auth.transport import requests
from google.oauth2 import service_account

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)
TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'  # nosec


class MailProcessor(object):
    def __init__(self):
        credentials, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/iam'])
        delegated_credentials = self.get_delegated_credentials(credentials)
        self.mail_service = googleapiclient.discovery.build(
            'gmail', 'v1', credentials=delegated_credentials, cache_discovery=False)
        self.mail_addresses = config.MAIL_ADDRESSES

    @staticmethod
    def get_delegated_credentials(credentials):
        try:
            request = requests.Request()
            credentials.refresh(request)

            signer = iam.Signer(request, credentials, config.GMAIL_SERVICE_ACCOUNT)
            creds = service_account.Credentials(
                signer=signer,
                service_account_email=config.GMAIL_SERVICE_ACCOUNT,
                token_uri=TOKEN_URI,
                scopes=config.GMAIL_SCOPES,
                subject=config.GMAIL_SUBJECT_ADDRESS)
        except Exception:
            raise

        return creds

    def generate_mail(self, mail_template):
        msg = MIMEMultipart('alternative')
        msg['From'] = config.GMAIL_REPLYTO_ADDRESS
        msg['Subject'] = config.SUBJECT
        msg['To'] = self.mail_addresses[0]

        if len(self.mail_addresses) > 1:
            msg['Bcc'] = ','.join(self.mail_addresses[1:])

        msg.attach(MIMEText(open(mail_template, 'r').read(), 'html'))
        raw = base64.urlsafe_b64encode(msg.as_bytes())
        raw = raw.decode()

        return {'raw': raw}

    def send_mails(self, mail_template):
        try:
            mail_body = self.generate_mail(mail_template)
            message = (self.mail_service.users().messages().send(userId="me", body=mail_body).execute())
            logging.info(f"Email '{message['id']}' has been sent to {len(self.mail_addresses)} recipients")
            return True
        except errors.HttpError as e:
            logging.error('An exception occurred when sending an email: {}'.format(e))
            return False
