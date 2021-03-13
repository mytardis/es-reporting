## Data reporting for MyTardis

This script will populate Elasticsearch initial index for reporting from MyTardis datafile records. It can also add new or update existing data for a time period.

We will support MyTardis version 4.2+

### Technical details

Settings are available through default setting.yaml config file.

You must specify credentials to the database and location of Elasticsearch server. You can increase number of rows fetched per single bulk call.

Run from command line:

```
python index.py [-h] [--config CONFIG] [--index INDEX] [--days DAYS] [--rebuild]

optional arguments:
  --config CONFIG  Config file location.
  --index INDEX    Index name to populate, default is * to include all indexes.
  --days DAYS      Populate only data for a number of past days, default is -1 to index all data.
  --rebuild        Delete and create index.
```

### Docker and Kubernetes

We build automatically the latest version of Docker image and publish it on DockerHub with [mytardis/es-reporting:latest](https://hub.docker.com/r/mytardis/es-reporting) image name.

Sample files in [kubernetes](./kubernetes/) folder will provide you with example of running this tool in Kubernetes.

### User activity log

How to log user activity in MyTardis:

```
if getattr(settings, "ENABLE_EVENTLOG", False):
    from tardis.apps.eventlog.utils import log
    log(
        action="USER_ACTION_TO_LOG",
        user=user,
        extra={
            "key1": "value1",
            "key2": "value2"
        }
    )
```

Parameters:

* `action` - unique identifier of action (in uppercase using underscores)
* `user` - user object (request.user)
* `obj` - any associated object (we will extract object_type and object_id)
* `extra` - any key:value dictionary for post-processing

### User activity export

To export data from user activity to Elasticsearch you will need to create exporter config in `indexes` folder, extending `ua` class.

Please refer to a simple example in `ua_user_login_success.py` file or advanced conversion in `ua_download_datafile.py` file, where event data extended with more information.

