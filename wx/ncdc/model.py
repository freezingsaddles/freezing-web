from dateutil import parser

class BaseCollection(object):
    """
    """
    totalCount = None
    
    def __init__(self, getter, result=None):
        self.getter = getter
        if result:
            self.parse(result)
    
    def parse(self, result):
        raise NotImplementedError()

class PagedCollection(object):
    
    pageCount = None
    _page = None
    
    def __init__(self, getter, result=None):
        self.getter = getter
        if result:
            self.parse(result)

    def next_page(self):
        self.page += 1
        self.parse(self.getter(page=self.page))
    
    def has_next_page(self):
        return self.pageCount is not None and self.page < self.pageCount
    
    @property
    def page(self):
        if self._page is None or self._page == 0:
            self._page = 1
        return self._page
    
    @page.setter
    def page(self, v):
        self._page = v
    
    def parse(self, result):
        raise NotImplementedError()

            
class SearchResultCollection(PagedCollection):
    results = None
    
    
class LocationSearchResultCollection(SearchResultCollection):
    
    def parse(self, result):
        obj = result['searchResultCollection']
        try:            
            self.totalCount = int(obj['@totalCount'])
        except KeyError:
            self.totalCount = 0
        try:
            self.pageCount = int(obj['@pageCount'])
        except KeyError:
            self.pageCount = 0
        try:
            self.results = [LocationSearchResult(**res) for res in obj['searchResult']]
        except KeyError:
            self.results = []

class DataCollection(BaseCollection):
    
    def parse(self, result):
        obj = result['dataCollection']
        self.observations = {}
        
        if obj:
            self.totalCount = int(obj['@totalCount'])
            self.observations = {}
            for d_obj in obj['data']:
                if isinstance(d_obj, dict): # There is some odd data out there.
                    od = ObservationData(date=parser.parse(d_obj['date']),
                                         dataType=d_obj['dataType'][0],
                                         value=d_obj['value'])
                    self.observations[od.dataType] = od

    def __iter__(self):
        return iter(self.observations.values())
    
class ObservationData(object):
    def __init__(self, date, dataType, value):
        self.date = date
        self.dataType = dataType
        self.value = value

class DesiredObservations(object):
    
    def __init__(self, attributes_wanted):
        self.observations = {}
        self.attributes_wanted = set(attributes_wanted)
    
    @property
    def observations_needed(self):
        return self.attributes_wanted - set(self.observations.keys())
    
    def fill(self, collection, overwrite=False):
        for o in collection:
            if overwrite or o.dataType in self.observations_needed:
                self.observations[o.dataType] = o
        
    
class LocationSearchResult(object):
    
    _minDate = None
    _maxDate = None
    
    def __init__(self, name=None, number=None, state=None, score=None, inCart=None, country=None,
                 inDateRange=None, type=None, id=None, minDate=None, maxDate=None):
        self.name = name
        self.number=number
        self.state = state
        self.score = score
        self.inCart = inCart
        self.country = country
        self.inDateRange = inDateRange
        self.type = type
        self.id = id
        self.minDate = minDate
        self.maxDate = maxDate
    
    @property
    def minDate(self):
        return self._minDate
    
    @minDate.setter
    def minDate(self, v):
        if v is not None:
            v = parser.parse(v)
        self._minDate = v
    
    @property
    def maxDate(self):
        return self._maxDate
    
    @maxDate.setter
    def maxDate(self, v):
        if v is not None:
            v = parser.parse(v)
        self._maxDate = v
    
    def __repr__(self):
        return '<{cls} id={id} name={name}>'.format(cls=self.__class__.__name__,
                                                 id=self.id, name=self.name)



class WeatherData(object):
    required_attribs = ('TMAX', 'TMIN', 'PRCP', 'SNOW')
    
    