import zipfile
import properties as properties
import datetime
import logging

def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))

class TimeProperty(dict):
    @property
    def times(self):
        return list(self.keys())

    @property
    def vals(self):
        return list(self.values())

class FileHandler():
    def __init__(self, path) -> None:
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall("")

        filename = path[path.rfind("\\")+1:]
        with open(f"{filename[:-8]}txt.acmi", errors="ignore") as f:
            self._lines = f.readlines()
            
    @property
    def lines(self):
        return self._lines.copy()

class Event():
    def __init__(self, eventType, message) -> None:
        self._eventType = eventType
        self._message = message

    @property
    def eventType(self):
        return self._eventType
    
    @property
    def message(self):
        return self._message

class Object():
    def __init__(self, id, reference) -> None:
        self._id = id
        self._reference = reference
        self._events = {}
        if self._id == 0:
            for prop in properties.GLOBAL_PROPERTIES:
                setattr(self, prop, TimeProperty())
        else:
            for prop in properties.OBJECT_PROPERTIES:
                setattr(self, prop, TimeProperty())

    @property
    def reference(self):
        return self._reference

    def decode(self, arr):
        for e in arr:
            val = e.split("=")
            if val[0] == "T":
                tr = val[1].split("|")
                props = properties.TRANSFORMATION_PROPERTIES[len(tr)]
                for i in range(len(tr)):
                    prop = props[i]
                    if hasattr(self, prop):
                        if tr[i] != '':
                            getattr(self, prop)[self._reference.timeNow] = float(tr[i])
            else:
                if hasattr(self, val[0]):
                    if val[1] != '':
                        getattr(self, val[0])[self._reference.timeNow] = properties.PROPERTIES[val[0]](val[1])

    def getProperty(self, prop, propertyTime = None):
        if hasattr(self, prop):
            if len(list(getattr(self, prop).values())) == 0: return None
            elif len(list(getattr(self, prop).values())) == 1:
                return list(getattr(self, prop).values())[0]
            else:
                v = getattr(self, prop)
                if propertyTime is None:
                    return getattr(self, prop)
                else:
                    return v[nearest(list(v.keys()), propertyTime)]

    def addEvent(self, time, event: Event):
        self._events[time] = event

    def getEventsByType(self, eventType: str):
        events = {}
        for time, event in self._events.items():
            if event.eventType == eventType:
                events[time] = event
        return events

class Reference(Object):
    _timeNow = datetime.timedelta(0, 0)  
    _ReferenceTime = {}
    
    def __init__(self, id) -> None:
        super().__init__(id, self)

    @property
    def timeNow(self):
        if self.getProperty('ReferenceTime') is not None:
            return self.getProperty('ReferenceTime') + self._timeNow
        return datetime.datetime(1, 1, 1, 0, 0) + self._timeNow

    @timeNow.setter
    def timeNow(self, newTime):
        self._timeNow = datetime.timedelta(0, newTime)  
        
    def decode(self, arr):
        super().decode(arr)
        for e in arr:
            if "AuthenticationKey" not in e:
                vals = e.split("=")
                logging.info(f"TacviewParser: {vals[0]}: {vals[1]}")

class TacviewParser():
    def __init__(self, filename) -> None:
        self._fileHandler = FileHandler(filename)
        self._lines = self._fileHandler.lines
        self._objects = {}
        self._reference = Reference(id = 0)

    def decode(self):
        for line in self._lines:
            self.decodeLine(line.replace("\n", ""))

    def decodeLine(self, line):
        if "//" in line:
            line = line[:line.find("//")]
        if "#" == line.strip()[0]:
            self._reference.timeNow = float(line[1:])
        elif "Event" in line:
            pass
        elif "-" == line.strip()[0]:
            id = int(line.strip()[1:], 16)
            if id  in self._objects:
                obj = self._objects[id]
                obj.addEvent(self._reference.timeNow, Event("Removed", ""))
        else:
            arr = line.split(',')
            if len(arr) > 1:
                id = int(arr[0], 16)
                if id not in self._objects:
                    if id == 0:
                        self._objects[id] = self._reference
                        self._reference.decode(arr[1:])   
                        logging.info(f"TacviewParser: Created reference object with ID = {id} at time = {self._reference.timeNow}") 
                    else:
                        obj = Object(id, self._reference)
                        obj.decode(arr[1:])
                        obj.addEvent(self._reference.timeNow, Event("Created", ""))
                        self._objects[id] = obj
                        logging.debug(f"TacviewParser: Created object with ID = {id} at time = {self._reference.timeNow}, pilot = {obj.getProperty('Pilot')}, type = {obj.getProperty('Type')}")
                else:
                    obj = self._objects[id]
                    obj.decode(arr[1:])

    @property
    def objects(self):
        return self._objects

    def getObjectsByProperty(self, prop, value):
        objs = []
        for _, obj in self._objects.items():
            if obj.getProperty(prop) == value:
                objs.append(obj)
        return objs

