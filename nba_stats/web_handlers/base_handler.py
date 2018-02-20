import logging
log = logging.getLogger('stats')


class BaseHandler:

    def __init__(self, base_url=None, model=None):
        log.debug("Creating a {c}".format(c=self.__class__.__name__))
        self.base_url = base_url
        self.raw_data = None
        self.obj_list = []
        self.model = model

    def _get_data(self, index):
        data = self.raw_data['resultSets'][index]
        headers = data['headers']
        rows = data['rowSet']
        return [dict(zip(headers, row)) for row in rows]

    def fetch_raw_data(self, *args, **kwargs):
        pass

    def parse(self):
        pass

    def create(self):
        if len(self.obj_list) == 0:
            log.debug("No objects to create.")
        else:
            log.debug("Begin bulk create call for {c}".format(c=self.model.__name__))
            self.model.objects.bulk_create(self.obj_list)
            log.debug("Bulk create call was successful.")