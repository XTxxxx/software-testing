class TraceEntry:
    def __init__(
        self,
        data: dict
    ):
        self.data = data
    
    def _region(self):
        if self.data['locations'][0]['physicalLocation'].get('region'):
            return self.data['locations'][0]['physicalLocation']['region']
        return None
    def _logical(self):
        if self.data['locations'][0].get('logicalLocation'):
            return self.data['locations'][0]['logicalLocation']
        return None
    def _artifact(self):
        return self.data['locations'][0]['physicalLocation']['artifactLocation']
    
    def start_line(self):
        if self._region():
            return self._region()['startLine']
        return 0
    
    def end_line(self):
        if self._region():
            return self._region()['startLine']
        return 0
    
    def start_column(self):
        if self._region():
            return self._region().get('startColumn')
        return 0
    
    def end_column(self):
        if self._region():
            return self._region().get('endColumn')
        return 0
    
    def name(self):
        if self._logical():
            return self._logical().get('name')
        return ""
    
    def kind(self):
        if self._logical():
            return self._logical().get('kind')
        return ""
    
    def fullyQualifiedName(self):
        if self._logical():
            return self._logical().get('fullyQualifiedName')
        return ""
    
    def uri(self):
        uri = self._artifact()['uri']
        if self._artifact().get('uriBaseId'):
            uri = self._artifact()['uriBaseId'] + uri
        return uri
    
    def message(self):
        return self.data['message'].get('text')
    
    def rule_id(self):
        return self.data['ruleId']
    
    

    def __eq__(self, other):
        if abs(self.start_line() - other.start_line()) < 100 and\
            abs(self.end_line() - other.end_line()) < 100 and\
            self.start_column() == other.start_column() and\
            self.end_column() == other.end_column() and\
            self.uri() == other.uri() and\
            self.message() == other.message() and\
            self.name() == other.name() and\
            self.kind() == other.kind() and\
            self.fullyQualifiedName() == other.fullyQualifiedName():
            return True
        return False
    

class Warning:
    def __init__(
        self,
        trace_base: TraceEntry,
    ):
        self.trace = [trace_base]
    
    def try_add_trace(self, result: dict):
        last_trace = self.trace[-1]
        toAdd = TraceEntry(result)
        same = bool(last_trace == toAdd)
        if same == True:
            self.trace.append(toAdd)
        return same

def to_warning(result: dict):
    return Warning(TraceEntry(result))