from .ua import UserActionIndex


class ReportingIndex(UserActionIndex):

    def __init__(self, cur, index_name):
        super().__init__(cur, index_name, "DOWNLOAD_DATAFILE")
