# Agent log script

## Install dependencies
You should have python 3 installed, the only dependency you will need is `pandas` and you can run the command below to install it.

```shell
 pip install -r requirements.txt 
```

## Run script
```shell
python3 compute_latency.py -i "path_to_agent_logs_directory"
```

Outputs:
Mean, Max, count, standard deviation, 25th, 50th and 75th percentile as such:

<b>Values are in ms</b>

| Tables        | duration_without_backoff  | duration  |
| ------------- |:-------------:            | -----:    |
| count         | 14.0                      | 14.0      |
| mean          | 134.3                     |   341.4   |
| std           | 34.5                      |    46.7   |
| 25%            | 34.5                     |    305.0  |
| 50%          | 34.5                       |    324.5  |
| 75%            | 144.0                    |    353.2  |
| max            | 227.0                    |    479.0  |

Note: this script will read all logs that are present in the specified directory. Please make sure you only have agent log files.


## About the script's inner workings

We first compute the starting timestamp, which is the first `MessageService` call minus the duration of that call, let's call it `t_start` (timestamp)

We then compute the backoff (sleep) time spent between each retry of the `ObjectStatus` call and `retrieveMessagePayload` call, let's call it `d_retry` (duration)

Finally, we fetch the timestamp of the last `retrieveMessagePayload` call made, let's call it `t_end`

The `duration` field is simply `t_start - t_end`.

The `duration_without_backoff` is `(t_start - t_end) - d_retry`

<br>


|   type    | traceid   | url     | status  | date  | time    | duration | unit |
| :--------:|:---------:|:-------:|:-------:|:-----:|:-------:|:--------:| -----:|
|OUTGOING_REQUEST|23Rfte|webcontroller/ingestor/v2/MessageService|200|2021-04-19|2021-06-29 16:12:04.796000|43|ms|
|OUTGOING_REQUEST|23Rfte|webcontroller/ingestor/v1/ObjectStatus|200|2021-04-19|2021-06-29 16:12:04.811000|15|ms|
|OUTGOING_REQUEST|23Rfte|webcontroller/ingestor/v1/ObjectStatus|200|2021-04-19|2021-06-29 16:12:04.927000|16|ms|
|OUTGOING_REQUEST|23Rfte|dataquery/retrieveMessagePayload|404|2021-04-19|2021-06-29 16:12:04.944000|17|ms|
|OUTGOING_REQUEST|23Rfte|dataquery/retrieveMessagePayload|404|2021-04-19|2021-06-29 16:12:05.064000|19|ms|
|OUTGOING_REQUEST|23Rfte|dataquery/retrieveMessagePayload|200|2021-04-19|2021-06-29 16:12:05.236000|21|ms|


In this specific case:

`t_start =  2021-06-29 16:12:04.796 - 43 = 2021-06-29 16:12:04.753`

`t_end = 2021-06-29 16:12:05.236`

`duration` would be equal to `483 ms` (which is what is output by this script)
