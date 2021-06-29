# Agent log script

## Install dependencies
You should have python 3 installed, the only dependency you will need is `pandas` and you can run the command below to install it.

```shell
 pip install -r requirements.txt 
```

## Run script
```shell
python3 -i "path_to_agent_logs_directory"
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
