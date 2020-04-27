## Data reporting for MyTardis

This script will populate Elasticsearch initial index for reporting from MyTardis datafile records. It can also add new or update existing data for a time period.

We will support MyTardis version 4.2+

### Technical details

Settings are available through default setting.yaml config file.

You must specify credentials to the database and location of Elasticsearch server. You can increase number of rows fetched per single bulk call.

Run from command line:

```
python index.py [--config CONFIG] [--days DAYS] [--rebuild]

optional arguments:
  --config CONFIG  Config file location.
  --days DAYS      Populate past DAYS of data only, default is -1 to index all data.
  --rebuild        Delete and create index.
```

### Docker and Kubernetes

We build automatically latest version of Docker image and publish it on DockerHub with mytardis/es-reporting:latest image name.

Sample files in [kubernetes](./kubernetes/) folder will provide you with example of running this tool in Kubernetes.