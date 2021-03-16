from google.cloud import logging as cloud_logging
import datetime
import time
import logging
import os
import sys
import argparse

logging.basicConfig(level=logging.INFO)


def request_log(cloud_logger, project_id, function_name):
    # Get timestamp of one minute ago
    time_stamp = time_format((datetime.datetime.utcnow() - datetime.timedelta(seconds=60)))
    logging.info("Filtering logs on timestamp: {}".format(time_stamp))

    log_filter = "severity = INFO " \
                 "AND resource.labels.function_name = \"{}\" " \
                 "AND timestamp >= \"{}\" ".format(function_name, time_stamp)

    # Get all logs with the log filter
    entries = cloud_logger.list_entries(
        filter_=log_filter, order_by=cloud_logging.DESCENDING,
        resource_names=["projects/{}".format(project_id)])

    return entries


def time_format(dt):
    return "%s:%.3f%sZ" % (
        dt.strftime('%Y-%m-%dT%H:%M'),
        float("%.3f" % (dt.second + dt.microsecond / 1e6)),
        dt.strftime('%z')
    )


def logging_check(function_name, logging_message, max_execution_time):
    logging.info("Checking logs for message '{}'".format(logging_message))
    # First wait on the execution of the function that puts XML files on Azure
    cloud_client = cloud_logging.Client()
    log_name = 'cloudfunctions.googleapis.com%2Fcloud-functions'
    cloud_logger = cloud_client.logger(log_name)
    # Project id where the function is
    # If function is not in the same project ID of where this function is executed,
    # a delegated SA should be added
    project_id = os.environ.get('PROJECT_ID')

    start_time = time.time()
    # Could take some time before other function has logged
    entries_list = []
    finished = False
    while True:
        if time.time() - start_time > max_execution_time:
            # No logs were found within time limit
            # Other function has probably not been called
            logging.info("No logs of function {} were found within the time limit".format(function_name))
            break
        else:
            logging.info('Refreshing logs of function {}...'.format(function_name))
            entries = request_log(cloud_logger, project_id, function_name)
            for entry in entries:
                entries_list.append(entry.payload)

            for i in range(len(entries_list)):
                if(i-1 >= 0):
                    if('Function execution started' in entries_list[i]
                       and 'Function execution took' not in entries_list[i-1]):
                        logging.info("The execution of function {} has not yet finished".format(function_name))
                        finished = False
                    else:
                        logging.info("The execution of function {} has finished".format(function_name))
                        finished = True

            if finished:
                # Check if the function logged the right message as last
                if(logging_message in entries_list[0]):
                    logging.info("Last message in logging was '{}'".format(logging_message))
                    finished = True
                else:
                    logging.info("Last message in logging was not '{}'".format(logging_message))
                    finished = False
            # If logs have been found
            if entries_list and finished:
                break
            time.sleep(10)
    if not entries_list or finished is False:
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--function-name', required=True)
    parser.add_argument('-l', '--logging-message', required=True)
    parser.add_argument('-e', '--execution-time', required=True)
    args = parser.parse_args()
    function_name = args.function_name
    logging_message = args.logging_message
    max_execution_time = args.execution_time
    check_logging_bool = logging_check(function_name, logging_message, int(max_execution_time))
    if check_logging_bool is False:
        logging.error("The logging message '{}' could not be found within {} seconds".format(logging_message, max_execution_time))
        sys.exit(1)
    logging.info("Logging was found")
