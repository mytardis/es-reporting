from datetime import datetime, timedelta
from psycopg2 import sql


def get_filters(days, start_id):

    filters = [
        sql.SQL("dfo.verified = True"),
        sql.SQL("dfo.id > {}".format(start_id))
    ]

    if days != -1:
        rewind = datetime.now() + timedelta(-days)
        filters.append(
            sql.SQL("dfo.created_time >= '{}'".format(rewind.date()))
        )

    return sql.SQL(" AND ").join(filters)


def count_from_db(cur, days, start_id):

    q = sql.SQL('''
        select count(dfo.id) as total
        from tardis_portal_datafileobject dfo
        where {}
    ''').format(
        get_filters(days, start_id)
    )

    cur.execute(q)
    rows = cur.fetchall()

    return rows[0]["total"]


def data_from_db(cur, days, start_id, rows_bulk):

    q = sql.SQL('''
        select
            dfo.id as dfo_id,
            dfo.created_time as uploaded_time,
            df.created_time as created_time,
            df.size as file_size,
            sb.id as storagebox_id,
            sb.description as storagebox_name,
            ds.id as dataset_id,
            ds.description as dataset_name,
            i.id as instrument_id,
            i.name as instrument_name,
            f.id as facility_id,
            f.name as facility_name,
            0 as experiment_id,
            'Unknown' as experiment_name,
            0 as uploader_id,
            'Unknown' as uploader_name,
            0 as user_id,
            'Unknown' as user_name
        from tardis_portal_datafileobject dfo
        left join tardis_portal_datafile df
        on df.id = dfo.datafile_id
        left join tardis_portal_dataset ds
        on ds.id = df.dataset_id
        left join tardis_portal_instrument i
        on i.id = ds.instrument_id
        left join tardis_portal_facility f
        on f.id = i.facility_id
        left join tardis_portal_storagebox sb
        on sb.id = dfo.storage_box_id
        where {}
        order by dfo.id asc
        limit {}
    ''').format(
        get_filters(days, start_id),
        sql.Literal(rows_bulk)
    )

    cur.execute(q)
    rows = cur.fetchall()

    return rows


def get_extras(cur, dataset_ids):

    q = '''
        select
            dse.dataset_id,
            dse.experiment_id as experiment_id,
            e.title as experiment_name,
            s.name as schema_name,
            pn.name as parameter_name,
            ep.string_value as parameter_value,
            up.id as uploader_id,
            up.name as uploader_name,
            u.id as user_id,
            trim(concat(u.first_name, ' ', u.last_name)) as user_name
        from tardis_portal_dataset_experiments dse
        left join tardis_portal_experiment e
        on e.id = dse.experiment_id
        left join tardis_portal_experimentparameterset eps
        on eps.experiment_id = dse.experiment_id
        left join tardis_portal_experimentparameter ep
        on ep.parameterset_id = eps.id
        left join tardis_portal_schema s
        on s.id = eps.schema_id
        left join tardis_portal_parametername pn
        on pn.id = ep.name_id
        left join mydata_uploader up
        on
            s.name = 'MyData Default Experiment' and
            pn.name = 'uploader' and
            up.uuid = ep.string_value
        left join auth_user u
        on
            s.name = 'MyData Default Experiment' and
            pn.name = 'user_folder_name' and
            u.username = ep.string_value
        where dse.dataset_id in %s
        order by dse.dataset_id , dse.experiment_id
    '''

    cur.execute(q, [tuple(dataset_ids)])
    rows = cur.fetchall()

    data = {}
    for row in rows:
        ds_id = row["dataset_id"]
        if ds_id not in data:
            data[ds_id] = {
                "experiment_id": row["experiment_id"],
                "experiment_name": row["experiment_name"]
            }
        if row["uploader_id"] is not None:
            data[ds_id]["uploader_id"] = row["uploader_id"]
            data[ds_id]["uploader_name"] = row["uploader_name"]
        if row["user_id"] is not None:
            data[ds_id]["user_id"] = row["user_id"]
            data[ds_id]["user_name"] = row["user_name"]

    return data


def data_to_es(index_name, data):

    for item in data:
        yield {
            '_index': index_name,
            '_type': '_doc',
            '_id': item["dfo_id"],
            '_source': item
        }
