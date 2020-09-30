class BaseReportingIndex:

    def __init__(self, cur, index_name):
        self.cur = cur
        self.index_name = index_name
        self.cache = {}

    def count_from_db(self, days, start_id):
        pass

    def data_from_db(self, days, start_id, rows_bulk):
        pass

    def transform_data(self, start, rows, cache=None):
        pass

    def data_to_es(self, data):
        pass
