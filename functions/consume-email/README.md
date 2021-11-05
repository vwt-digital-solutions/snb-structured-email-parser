# Consume Email
This function consumes messages containing e-mails posted on a Pub/Sub Topic, parses them and sends them to another topic.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    DEBUG_LOGGING = Set this to True if you want the debugging logging to show
    SENDER = E-mail address where e-mails should come from
    ID = A list containing e-mail fields where the ID of the message can be build from
    REQUIRED_FIELDS = The fields that should be gotten from the e-mail and send to a topic
    TOPIC_NAME = The name of the topic where the e-mails should be send to when parsed
    TOPIC_PROJECT_ID = The project id that contains the topic
    ~~~
2. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## Incoming message
To make sure the function works according to the way it was intented, the incoming messages from a Pub/Sub Topic must have the following structure based on the [company-data structure](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema):
~~~JSON
{
  "gobits": [ ],
  "email": {
    "sent_on": "datetime",
    "received_on": "datetime",
    "subject": "subject of e-mail",
    "sender": "sender e-mail address",
    "recipient": "recipient e-mail address",
    "body": "html-body",
    "attachments": []
  }
}
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
