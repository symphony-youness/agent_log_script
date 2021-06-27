#!/usr/bin/python3

import getopt
import sys
import re

from collections import defaultdict
from pathlib import Path

import pandas as pd


def argument_handler(argv):
    input_path = ""
    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print("compute_latency.py -i <input dir path>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("compute_latency.py -i <input dir path>")
            sys.exit()
        elif opt in ("-i", "--ifile"):
            input_path = arg

    print("Input dir path is ", input_path)
    return input_path


def list_log_files(dir_path: Path):
    logs_dir = Path(dir_path)
    return [e for e in logs_dir.glob("*.log")]


def process_incoming_request(line):
    trace_id = line[8][:-1]
    url = line[13][:-1]
    url = re.sub(r'(/.{34,36}/)', "/{id}/", url)
    status = line[11][:-1]
    date = line[0]
    time = line[1]
    duration = line[-1]
    time_unit = line[-2][:-1]
    return ["INCOMING_REQUEST", trace_id, url, status, date, time, duration, time_unit]


def process_outgoing_requests(line):
    trace_id = line[8][:-1]
    url = line[15][:-1]
    status = line[17][:-1]

    if url == "200" or url == "404":
        return

    if "symphony" in url:  # trim https
        url = "/".join(url.split("/")[3:])

    url = re.sub(r'(/.{34,36}/)', "/{id}/", url)  # Removes id

    if "?" in url:  # trim url part with parameters
        url = url.split("?")[0]

    date = line[0]
    time = line[1]
    duration = int(line[-2])
    time_unit = line[-1]
    return ["OUTGOING_REQUEST", trace_id, url, status, date, time, duration, time_unit]


def process_log_files(log_files):
    OUTGOING_REQUESTS = "[com.symphony.agent.filters.InternalRequestLogFilter]"
    data = []
    for log_file in log_files:
        with open(log_file) as infile:
            for line in infile:
                line = line.strip().split(" ")
                if len(line) > 4:
                    if line[4] == OUTGOING_REQUESTS:
                        row = process_outgoing_requests(line)
                        if row is not None:  # To handle the case of mis-shaped logs (url = 200 or 400)
                            data.append(row)
    return data


def build_dataframe(data):
    columns = ["type", "traceid", "url", "status", "date", "time", "duration", "unit"]
    conversion_dict = {"duration": int}
    return pd.DataFrame(data, columns=columns).astype(conversion_dict)


def get_ingestion_duration(df):
    # total_time = last_ret_msg_payload - (timestamp_message_service - duration) - (retry_time(number_object_status_calls) - (retry_time(number_ret_pay_calls))
    continue_count = defaultdict(int)
    grouped_df = df.groupby("traceid")
    duration_list = []
    duration_without_backoff_list = []
    traceid_list = []
    retries = []
    for key, item in grouped_df:
        group = grouped_df.get_group(key)
        group.sort_values(by="time", inplace=True)

        msg_srv_grp = group[group.url == "webcontroller/ingestor/v2/MessageService"]
        msg_srv_count = len(msg_srv_grp)

        obj_status_grp = group[group.url == "webcontroller/ingestor/v1/ObjectStatus"]
        obj_status_count = len(obj_status_grp)
        obj_status_retry_backoff_time = get_backoff_time(obj_status_count)

        ret_payload_grp = group[group.url == "dataquery/retrieveMessagePayload"]
        ret_payload_count = len(ret_payload_grp)
        ret_payload_retry_backoff_time = get_backoff_time(ret_payload_count)

        if msg_srv_count > 0:
            message_service = msg_srv_grp.iloc[0]
            message_service_real_timestamp = message_service.time - pd.offsets.Milli(message_service.duration)
        else:
            continue_count["msg_srv"] += 1
            continue

        if ret_payload_count > 0:
            last_ret_payload = ret_payload_grp.iloc[-1]
            last_timestamp = last_ret_payload.time
        else:
            continue_count["ret_pay"] += 1
            continue

        ingestion_duration = last_timestamp - message_service_real_timestamp
        ingestion_duration_without_backoff = ingestion_duration - pd.offsets.Milli(
            int(obj_status_retry_backoff_time)) - pd.offsets.Milli(int(ret_payload_retry_backoff_time))

        duration_list.append(ingestion_duration.total_seconds() * 1000)
        duration_without_backoff_list.append(ingestion_duration_without_backoff.total_seconds() * 1000)
        traceid_list.append(message_service.traceid)
        retries.append(obj_status_count - 1)

    d = {"traceid": traceid_list, "duration_without_backoff": duration_without_backoff_list, "duration": duration_list,
         "retries": retries}
    print("continue_count", continue_count)
    return pd.DataFrame(data=d)


def get_backoff_time(count):
    if count < 2:
        return 0
    backoff = 100
    time = 100
    i = 2
    while i < count:
        backoff = backoff * 1.5
        if backoff >= 1000:
            backoff = 1000
        time += backoff
        i += 1
    return time


def process_dataframe(df):
    outgoing_df = df.loc[df["type"] == "OUTGOING_REQUEST"]

    # take only 2 calls: "webcontroller/ingestor/v2/MessageService" and "webcontroller/ingestor/v1/ObjectStatus"
    reduced_df = outgoing_df[(outgoing_df.url == "webcontroller/ingestor/v2/MessageService")
                             | (outgoing_df.url == "webcontroller/ingestor/v1/ObjectStatus")
                             | (outgoing_df.url == "dataquery/retrieveMessagePayload")]
    reduced_df["time"] = pd.to_datetime(reduced_df["time"])

    # compute ingestion time
    return get_ingestion_duration(reduced_df)


def main(argv):
    input_path = argument_handler(argv)

    top_level_log_files = list_log_files(input_path)

    data = process_log_files(top_level_log_files)

    df = build_dataframe(data)

    duration_df = process_dataframe(df)

    print(duration_df.head().to_string())
    print(duration_df.describe().to_string())


if __name__ == "__main__":
    main(sys.argv[1:])
