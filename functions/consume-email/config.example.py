# To display debug messages, or not to display debug messages.
DEBUG_LOGGING = True or False

# Allowed sender e-mail addresses (lowercase).
SENDER_WHITELIST = [
    "foo@example.com",
    "bar@example.com"
]

# Fields that have to be extracted from the e-mail.
# Field names are lowercase, and spaces are replaced with underscores. This formatting does not matter in the
# actual e-mail's body.
FIELDS = [
    "some_field",
    "another_field"
]

# Field that will be used to get the e-mail's type. This field should also be configured in FIELDS.
TYPE_FIELD = "type_field"

# Values allowed for the specified TYPE_FIELD field.
ALLOWED_TYPES = [
    "SOME_TYPE",
    "ANOTHER_TYPE"
]

# GCloud project id with topic to send extracted data to.
TOPIC_PROJECT_ID = "topic-project-id"

# Name of the topic to send extracted data to.
TOPIC_NAME = "topic-name"
