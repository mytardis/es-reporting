from .ua import UserActionIndex


class ReportingIndex(UserActionIndex):

    def __init__(self, cur, index_name):
        super().__init__(cur, index_name, "DOWNLOAD_DATAFILE")

    def transform_data(self, start, rows, **kwargs):

        datafile_ids = list(set([row["extra"]["id"] for row in rows]))
        extra_df_ids = []

        for df_id in datafile_ids:
            if df_id not in self.cache:
                extra_df_ids.append(df_id)

        if len(extra_df_ids) != 0:
            extras = self.get_extras(extra_df_ids)
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

    def get_extras(self, datafile_ids):

        q = '''
            select
                df.id as datafile_id,
                df.size as file_size,
                ds.id as dataset_id,
                ds.description as dataset_name,
                i.id as instrument_id,
                i.name as instrument_name,
                f.id as facility_id,
                f.name as facility_name
            from tardis_portal_datafile df
            left join tardis_portal_dataset ds
            on ds.id = df.dataset_id
            left join tardis_portal_instrument i
            on i.id = ds.instrument_id
            left join tardis_portal_facility f
            on f.id = i.facility_id
            where df.id in %s
        '''

        self.cur.execute(q, [tuple(datafile_ids)])
        rows = self.cur.fetchall()

        data = {}
        for row in rows:
            df_id = row["datafile_id"]
            if df_id not in data:
                data[df_id] = {
                    "datafile_id": row["datafile_id"],
                    "file_size": row["file_size"],
                    "dataset_id": row["dataset_id"],
                    "dataset_name": row["dataset_name"],
                    "instrument_id": row["instrument_id"],
                    "instrument_name": row["instrument_name"],
                    "facility_id": row["facility_id"],
                    "facility_name": row["facility_name"]
                }

        return data
