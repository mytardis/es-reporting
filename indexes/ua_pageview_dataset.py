from .ua import UserActionIndex


class ReportingIndex(UserActionIndex):

    def __init__(self, cur, index_name):
        super().__init__(cur, index_name, "PAGEVIEW_DATASET")

    def transform_data(self, start, rows, **kwargs):

        dataset_ids = list(set([row["extra"]["id"] for row in rows]))
        extra_ds_ids = []

        for ds_id in dataset_ids:
            if ds_id not in self.cache:
                extra_ds_ids.append(ds_id)

        if len(extra_ds_ids) != 0:
            extras = self.get_extras(extra_ds_ids)
            for k in extras:
                self.cache[k] = extras[k]

        data = []
        for row in rows:
            if row["log_id"] > start:
                start = row["log_id"]
            extra = row["extra"]
            del(row["extra"])
            ds_id = int(extra["id"])
            if ds_id in self.cache:
                extra = {**extra, **self.cache[ds_id]}
                del (extra["id"])
            data.append({**row, **extra})

        return data, start

    def get_extras(self, dataset_ids):

        q = '''
            select
                ds.id as dataset_id,
                ds.description as dataset_name,
                i.id as instrument_id,
                i.name as instrument_name,
                f.id as facility_id,
                f.name as facility_name
            from tardis_portal_dataset ds
            left join tardis_portal_instrument i
            on i.id = ds.instrument_id
            left join tardis_portal_facility f
            on f.id = i.facility_id
            where ds.id in %s
        '''

        self.cur.execute(q, [tuple(dataset_ids)])
        rows = self.cur.fetchall()

        data = {}
        for row in rows:
            ds_id = row["dataset_id"]
            if ds_id not in data:
                data[ds_id] = {
                    "dataset_id": row["dataset_id"],
                    "dataset_name": row["dataset_name"],
                    "instrument_id": row["instrument_id"],
                    "instrument_name": row["instrument_name"],
                    "facility_id": row["facility_id"],
                    "facility_name": row["facility_name"]
                }

        return data
