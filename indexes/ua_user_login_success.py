from datetime import datetime, timedelta
from psycopg2 import sql


def get_filters(days, start_id):

    filters = [
        sql.SQL("l.id > {}".format(start_id))
    ]

    if days != -1:
        rewind = datetime.now() + timedelta(-days)
        filters.append(
            sql.SQL("l.timestamp >= '{}'".format(rewind.date()))
        )

    return sql.SQL(" AND ").join(filters)


def count_from_db(cur, days, start_id):

    q = sql.SQL('''
        select count(l.id) as total
        from eventlog_log l
        inner join eventlog_action a
        on a.id = l.action_id and a.name = 'USER_LOGIN_SUCCESS'
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
            l.id as log_id,
            l.timestamp,
            l.action_id,
            a.name as action_name,
            l.user_id,
            trim(concat(u.first_name, ' ', u.last_name)) as user_name,
            l.extra
        from eventlog_log l
        inner join eventlog_action a
        on a.id = l.action_id and a.name = 'USER_LOGIN_SUCCESS'
        left join auth_user u
        on u.id = l.user_id
        where {}
        order by l.id asc
        limit {}
    ''').format(
        get_filters(days, start_id),
        sql.Literal(rows_bulk)
    )

    cur.execute(q)
    rows = cur.fetchall()

    return rows


def transform_data(start, rows, **kwargs):

    data = []
    for row in rows:
        if row["log_id"] > start:
            start = row["log_id"]
        extra = row["extra"]
        del(row["extra"])
        data.append({**row, **extra})

    return data, start


def data_to_es(index_name, data):

    for item in data:
        yield {
            '_index': index_name,
            '_id': item["log_id"],
            '_source': item
        }
