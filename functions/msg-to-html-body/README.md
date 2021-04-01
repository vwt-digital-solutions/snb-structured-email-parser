# Consume Email
This function consumes messages containing e-mails posted on a Pub/Sub Topic, parses them and sends them to another topic.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    DEBUG_LOGGING = Set this to True if you want the debugging logging to show
    TOPIC_NAME = Topic where the email should be send to
    TOPIC_PROJECT_ID = Project id where the topic is
    TEMPLATE_PATH_FIELD = The field which can have as value one of the fields in HTML_TEMPLATE_PATHS
    TEMPLATE_PATH_FIELD_ROOT = Optional to add the root where the field can be found
    HTML_TEMPLATE_PATHS = Dictionary containing as its fields the values the TEMPLATE_PATH_FIELD can take
    RECIPIENT_MAPPING_MESSAGE_FIELD = Field in the message to look up the right dictionary in RECIPIENT_MAPPING
    RECIPIENT_MAPPING = Dictionary where the mail recipient can be looked up from using the Google Cloud Platform (GCP) Firestore
    SENDER = Email address of the sender
    ~~~
2. Make sure the following variables are present in the environment:
    ~~~
    DATA_SELECTOR = The identifier of the received message
    ~~~
3. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## HTML template paths
The ```HTML_TEMPLATE_PATHS``` field can look as follows:  
~~~JSON
{
    "TEMPLATE_PATH_FIELD_value_1": {
        "template_path": "directory_path_1",
        "template_args": {
            "arg_field": {
                "arg_field_value": "MESSAGE_FIELD"
            }
        },
        "mail_subject": {
            "subject_part_1": "HARDCODED or MESSAGE_FIELD",
            "subject_part_2": "HARDCODED or MESSAGE_FIELD",
            "subject_part_etcetera": "HARDCODED or MESSAGE_FIELD"
        }
    },
    "TEMPLATE_PATH_FIELD_value_2": {
        "template_path": "directory_path_1",
        "template_args": {
            "arg_field": {
                "arg_field_value": "MESSAGE_FIELD",
                "arg_field_format": "DATETIME"
            }
        },
        "mail_subject": {
            "subject_part_1": "HARDCODED or MESSAGE_FIELD",
            "subject_part_2": "HARDCODED or MESSAGE_FIELD",
            "subject_part_etcetera": "HARDCODED or MESSAGE_FIELD"
        }
    },
    "TEMPLATE_PATH_FIELD_value_etcetera": {
        "template_path": "directory_path_1_etcetera",
        "template_args": {
            "arg_field": {
                "arg_field_value": "MESSAGE_FIELD"
            }
        },
        "mail_subject": {
            "subject_part_1": "HARDCODED or MESSAGE_FIELD",
            "subject_part_2": "HARDCODED or MESSAGE_FIELD",
            "subject_part_etcetera": "HARDCODED or MESSAGE_FIELD"
        }
    }
}
~~~
The field ```template_args``` should be a dictionary containing arguments that have to be given to the templates.  
For now it can only have the value ```MESSAGE_FIELD```, which means the argument's value should come from the message field  
given as the ```arg_field_value```. The ```arg_field``` should be the argument that needs to be given to the HTML template.  
This value in the HTML template could need a *datetime* format, in that case add the field ```arg_field_format``` with as
 it's value ```DATETIME```.

The fields in the ```mail_subject``` field define what the subject consist of. Together, they make the subject of the email.  
They can be ```HARDCODED```, in that case the ```subject_part``` is the hardcoded value. Or they can be a ```MESSAGE_FIELD```  
in which case the ```subject_part``` is the field that should be looked up in the message. The ```TEMPLATE_PATH_FIELD_ROOT```  
is also taken into account here.

## HTML Templates
The HTML templates should be templates in HTML. An example:
~~~HTML
<div>
    <br />
    Dear Sir/Madam,<br />
    <br />
    We would like to inform you that your package with number { package_number } has arrived.<br />
    <br />
</div>
~~~
Where the value of ```package_number``` can be given with the field ```template_args```.

## Firestore recipient mapping
The dictionary given in the parameter ```RECIPIENT_MAPPING``` shows what e-mail address the mail should be send to.  
It looks as follows:  
~~~JSON
{
    "message_value": {
        "firestore_collection_name": "firestore_collection_name_1",
        "firestore_ids": [
            {"firestore_field_1": "firestore_value_1"},
            {"firestore_field_2": "firestore_value_2"},
            {"firestore_field_etcetera": "firestore_value_etcetera"},
        ],
        "firestore_value": "firestore_field"
    }
}
~~~
Where ```message_value``` is the value of the field defined in ```RECIPIENT_MAPPING_MESSAGE_FIELD```, which is looked up in the incoming message.  
```firestore_collection_name``` is the collection in the firestore where the code should look.  
```firestore_ids``` contain a list of dictionaries with as their field the firestore field which should fit the accompanying firestore value. They are the IDs that are used to look up the right value.  
The value defined for ```firestore_value``` is the field that gives the recipient, which is thus looked up by the right IDs.

## Incoming message
To make sure the function works according to the way it was intented, the incoming messages from a Pub/Sub Topic must have the following structure based on the [company-data structure](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema):
~~~JSON
{
  "gobits": [ ],
  "message_field": {
    "root_field": {
      "field_1": "value_1",
      "field_2": "value_2",
      "field_etcetera": "value_etcetera"
    }
  }
}
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
