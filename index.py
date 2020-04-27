import sys
import argparse
import os
import yaml
import json

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch, helpers

from reporting import count_from_db, data_from_db, get_extras, data_to_es


def init_es_index(index_name):

    with open("{}.json".format(index_name)) as f:
        config = json.load(f)

    es.indices.delete(
        index=index_name,
        ignore_unavailable=True
    )

    es.indices.create(
        index=index_name,
        body=config
    )


parser = argparse.ArgumentParser()
parser.add_argument(
    "--config",
    default="settings.yaml",
    help="Config file location."
)
parser.add_argument(
    "--days",
    type=int,
    default=1,
    help="Populate past days of data."
)
parser.add_argument(
    "--rebuild",
    action="store_true",
    help="Delete and create index."
)

args = parser.parse_args()

if os.path.isfile(args.config):
    with open(args.config) as f:
        settings = yaml.load(f, Loader=yaml.Loader)
else:
    sys.exit("Can't find settings.")

try:
    con = connect(
        host=settings["database"]["host"],
        port=settings["database"]["port"],
        user=settings["database"]["username"],
        password=settings["database"]["password"],
        database=settings["database"]["database"]
    )
except Exception:
    sys.exit("Can't connect to the database.")

try:
    es_host = "{}:{}".format(
        settings["elasticsearch"]["host"],
        settings["elasticsearch"]["port"]
    )
    es = Elasticsearch([es_host])
except Exception:
    con.close()
    sys.exit("Can't connect to the Elasticsearch.")

cur = con.cursor(cursor_factory=RealDictCursor)

if args.rebuild:
    print("Rebuild index.")
    init_es_index(settings["index"]["name"])

start = 0
to_go = 1
cache = {}

while to_go > 0:

    to_go = count_from_db(cur, args.days, start)
    print(
        "{:,} datafileobjects to index, {:,} datasets cached"
        .format(to_go, len(cache))
    )

    if to_go > 0:

        rows = data_from_db(cur, args.days, start, settings["index"]["limit"])

        dataset_ids = list(set([row["dataset_id"] for row in rows]))
        extra_ds_ids = []
        for ds_id in dataset_ids:
            if ds_id not in cache:
                extra_ds_ids.append(ds_id)
        if len(extra_ds_ids) != 0:
            extras = get_extras(cur, extra_ds_ids)
            for k in extras:
                cache[k] = extras[k]

        data = []
        for row in rows:
            if row["dfo_id"] > start:
                start = row["dfo_id"]
            ds_id = row["dataset_id"]
            if ds_id in cache:
                data.append({**row, **cache[ds_id]})
            else:
                data.append(row)

        helpers.bulk(es, data_to_es(settings["index"]["name"], data))

print("Completed.")
cur.close()
con.close()
