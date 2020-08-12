import sys
import argparse
import importlib
import os
import yaml
import json

from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch, helpers


def get_parser():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--config",
        default="settings.yaml",
        help="Config file location (default: settings.yaml)."
    )

    parser.add_argument(
        "--index",
        default="*",
        help="Index name (default: *)."
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

    return parser


def get_indexes(indexes_folder):
    files = []
    for file in os.listdir(indexes_folder):
        if file.endswith(".py"):
            files.append(file.replace(".py", ""))
    return files


def init_es_index(indexes_folder, index_name):

    index_settings_file = os.path.join(
        indexes_folder, "{}.json".format(index_name))

    if os.path.exists(index_settings_file):
        with open(index_settings_file) as file:
            config = json.load(file)
    else:
        config = None

    es.indices.delete(
        index=index_name,
        ignore_unavailable=True
    )

    es.indices.create(
        index=index_name,
        body=config
    )


args = get_parser().parse_args()

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
except Exception as e:
    sys.exit("Can't connect to the database - {}.".format(str(e)))

try:
    es_host = "{}:{}".format(
        settings["elasticsearch"]["host"],
        settings["elasticsearch"]["port"]
    )
    es = Elasticsearch([es_host])
except Exception as e:
    con.close()
    sys.exit("Can't connect to the Elasticsearch - {}.".format(str(e)))

cur = con.cursor(cursor_factory=RealDictCursor)

indexes_folder_name = "indexes"
indexes_folder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    indexes_folder_name)

if args.index == "*":
    indexes = get_indexes(indexes_folder)
else:
    indexes = [args.index]

for index in indexes:

    print("Index: {}.".format(index))

    cfg = settings["index"][index]
    index_name = cfg["name"]
    batch = cfg["limit"]

    try:
        idx = importlib.import_module(
            "{}.{}".format(indexes_folder_name, index))
    except Exception as e:
        cur.close()
        con.close()
        sys.exit("Can't import module {} - {}.".format(index, str(e)))

    if args.rebuild:
        print("Rebuild index.")
        init_es_index(indexes_folder, index)

    start = 0
    to_go = 1
    cache = {}

    while to_go > 0:
        to_go = idx.count_from_db(cur, args.days, start)
        if to_go > 0:
            print("{:,} rows to index (cache={:,})".format(to_go, len(cache)))
            rows = idx.data_from_db(cur, args.days, start, batch)
            data, start = idx.transform_data(start, rows, cur=cur, cache=cache)
            helpers.bulk(es, idx.data_to_es(index_name, data))

print("Completed.")
cur.close()
con.close()
