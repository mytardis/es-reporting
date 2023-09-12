import sys
import argparse
import importlib
import os
import yaml
import json
from datetime import datetime
from random import randint
import pandas as pd

from psycopg2 import connect, sql
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch, helpers
from zipfile import ZipFile


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

    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump data from the database to CSV file."
    )

    parser.add_argument(
        "--zip",
        action="store_true",
        help="Compress exported data."
    )

    parser.add_argument(
        "--flush",
        action="store_true",
        help="Flush database after data dump."
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


def get_file_name(path, ext):
    today = datetime.now().strftime("%Y%m%d")
    file_name = "eventlog_{}.{}".format(today, ext)
    while True:
        abs_file_name = os.path.join(path, file_name)
        if not os.path.exists(abs_file_name):
            return abs_file_name, file_name
        else:
            file_name = "eventlog_{}_{:02d}.{}".format(today, randint(1, 99),
                                                       ext)


def dump_data(connection, cursor, is_zip, is_flush):
    days = int(settings["dump"]["keep"])
    data_path = settings["dump"]["path"]
    if not os.path.exists(data_path):
        connection.close()
        sys.exit("Can't find folder to dump data to - {}.".format(data_path))

    abs_file_name, file_name = get_file_name(data_path, "csv")
    print("File: {}".format(file_name))
    print("Dumping data...")
    q = sql.SQL("""
        SELECT * FROM eventlog_log
        WHERE timestamp < NOW() - INTERVAL '%s DAY'
        ORDER BY id ASC
    """)
    cursor.execute(q, [days])
    f = open(abs_file_name, "w")
    t = 0
    while True:
        df = pd.DataFrame(cursor.fetchmany(1000))
        if len(df) == 0:
            break
        else:
            df.to_csv(f, index=False, header=(f.tell() == 0), encoding="utf-8")
            t += len(df)
    f.close()
    if t == 0:
        print("No data found, deleting file.")
        os.remove(abs_file_name)
    else:
        print("Exported {} records.".format(t))
        if is_zip:
            print("Compressing data file...")
            zip_abs_file_name, zip_file_name = get_file_name(data_path, "zip")
            with ZipFile(zip_abs_file_name, "w") as zip:
                zip.write(abs_file_name, file_name)
            os.remove(abs_file_name)
        if is_flush:
            print("Flushing database...")
            q = sql.SQL("""
                DELETE FROM eventlog_log
                WHERE timestamp < NOW() - INTERVAL '%s DAY'
            """)
            cursor.execute(q, [days])
            connection.commit()
    cursor.close()
    connection.close()
    print("Completed.")


args = get_parser().parse_args()

if os.path.isfile(args.config):
    with open(args.config) as f:
        settings = yaml.load(f, Loader=yaml.Loader)
else:
    sys.exit("Can't find settings.")

try:
    host = settings["database"]["host"]
    port = settings["database"]["port"]
    user = settings["database"]["username"]
    password = settings["database"]["password"]
    database = settings["database"]["database"]

    print('--host: {} -- port: {} -- user: {} -- password: {} -- database: {}'.format(host, port, user, password,
                                                                                      database))
    #     con = connect(
    #         host=settings["database"]["host"],
    #         port=settings["database"]["port"],
    #         user=settings["database"]["username"],
    #         password=settings["database"]["password"],
    #         database=settings["database"]["database"]
    #     )
    con = connect(host=host, port=port, user=user, password=password, database=database)
except Exception as e:
    sys.exit("Can't connect to the database - {}.".format(str(e)))

cur = con.cursor(cursor_factory=RealDictCursor)

if args.dump:
    dump_data(con, cur, args.zip, args.flush)
    sys.exit(0)

try:
    es_host = "{}:{}".format(
        settings["elasticsearch"]["host"],
        settings["elasticsearch"]["port"]
    )
    es = Elasticsearch([es_host])
except Exception as e:
    con.close()
    sys.exit("Can't connect to the Elasticsearch - {}.".format(str(e)))

indexes_folder_name = "indexes"
indexes_folder = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    indexes_folder_name)

if args.index == "*":
    indexes = list(settings["indexes"].keys())
else:
    indexes = [args.index]

print('-----> indexes: {}'.format(indexes))

for index_name in indexes:

    print("Index: {}.".format(index_name))

    cfg = settings["indexes"][index_name]
    batch = cfg["limit"]

    try:
        module = importlib.import_module("{}.{}".format(indexes_folder_name, cfg["module"]))
        print('module: {}'.format(module))
    except Exception as e:
        cur.close()
        con.close()
        sys.exit("Can't import module {} - {}.".format(index_name, str(e)))

    if args.rebuild:
        print("Rebuild index - {}".format(index_name))
        init_es_index(indexes_folder, index_name)

    start = 0
    to_go = 1

    cls = module.ReportingIndex(cur, index_name)

    while to_go > 0:
        to_go = cls.count_from_db(args.days, start)
        if to_go > 0:
            print("{:,} rows to index (cache={:,})".format(
                to_go, len(cls.cache)))
            rows = cls.data_from_db(args.days, start, batch)
            data, start = cls.transform_data(start, rows)
            helpers.bulk(es, cls.data_to_es(data))

print("Completed.")
cur.close()
con.close()
