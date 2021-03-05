# Chain test
This folder contains a file from which you can check the logging of a function and a file to send an e-mail from a Gmail server.

## Send Mail
1. Make sure a ```config.py``` file exists within the directory, based on the [config.py.example](config.py.example), with the correct configuration:
    ~~~
    GMAIL_SERVICE_ACCOUNT = The service account that has access to the API scopes defined in GMAIL_SCOPES
    GMAIL_SUBJECT_ADDRESS = The Gmail account from where the e-mail is send
    GMAIL_REPLYTO_ADDRESS = The mail address that is given as the sender in the e-mail
    GMAIL_SCOPES = A list containing the right API scopes
    MAIL_ADDRESSES = A list with e-mail addresses where the mail should be send to
    SUBJECT = The subject the e-mail should have
    ~~~
2. Make sure the following variables are present in the environment:
    ~~~
    PROJECT_ID = The Google Cloud Platform (GCP) project ID
    ~~~
2. Call the function with the following flag:  
    * ```--mail-template/-t```: The path to the HTML mail template that should be send as e-mail

## Check Logging
1. Make sure the following variables are present in the environment:
    ~~~
    PROJECT_ID = The Google Cloud Platform (GCP) project ID
    ~~~
2. Call the function with the following flags:  
    * ```--function-name/-f```: The function you want to check the logging from
    * ```--logging-message/-l```: (Part of) the message that should be in the last logging entry
    * ```--execution-time/-e```: The time for which you want to check the logging, in seconds
