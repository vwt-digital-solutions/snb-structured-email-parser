from diagrams import Cluster, Diagram, Edge

from diagrams.gcp.analytics import PubSub
from diagrams.gcp.compute import Functions

from diagrams.onprem.compute import Server

from diagrams.generic.network import Router

from diagrams.generic.device import Mobile

publish_edge = Edge(label="Publish")
consume_edge = Edge(label="Consume")
import_edge = Edge(label="Link2 import script from VWT Operations")
export_edge = Edge(label="Link2 export script from VWT Operations")
bucket_trigger_edge = Edge(label="Bucket trigger")

with Diagram("T-Mobile structured emails to topic", show=False):

    t_mobile = Mobile("T-Mobile")

    mailbox = Router("Mailbox")

    ews_server = Server("EWS Server")

    with Cluster("GCP Operational Data Hub Platform"):
        with Cluster("vwt-p-gew1-ns-tmob-problem-int"):
            mail_ingest_function = Functions("vwt-p-gew1-\nns-tmob-problem-int-\nmail-ingest-func")

            with Cluster("vwt-p-gew1-ns-tmob-problem-int-ewsemails"):
                mail_ingest_pubsub = PubSub("vwt-p-gew1-\nns-tmob-problem-int-\newsemails-push-sub")

            mail_parser_function = Functions("vwt-p-gew1-\nns-tmob-problem-int-\nemail-parser-func")

            status_mail_function = Functions("vwt-p-gew1-\nns-tmob-problem-int-\nemail-status-func")

            mail_ingest_function >> publish_edge >> mail_ingest_pubsub >> consume_edge >> mail_parser_function

            status_mail_function >> t_mobile

        with Cluster("Operational Data Hub"):
            with Cluster("vwt-p-gew1-\nodh-hub-\ntmobile-parsed-problem-emails "):
                mail_parser_pubsub = PubSub("vwt-p-gew1-\nodh-hub-\ntmobile-parsed-problem-emails-link2-\npush-sub")

            mail_parser_function >> mail_parser_pubsub

            with Cluster("vwt-p-gew1-\nodh-hub-\nns-link2-statuses "):
                link2_statuses_pubsub = PubSub("vwt-p-gew1-\nodh-hub-\nns-link2-statuses-\npush-sub")

            link2_statuses_pubsub >> status_mail_function

    t_mobile >> mailbox >> ews_server >> mail_ingest_function
