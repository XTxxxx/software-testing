import pandas as pd

class Trace:
    def __init__(
        self,
        file: str,
        line_number: int
    ):
        self.file = file
        self.line_number = line_number

class Warning:
    def __init__(
        self,
        type: str,
        cwe: str,
        message: str,
        file: str,
        start_line: int,
        end_line: int,
        start_column: int,
        end_column: int,
        flag: bool,
        tag_history: list[Trace]
    ):
        self.type = type
        self.cwe = cwe
        self.message = message
        self.file = file
        self.start_line = start_line
        self.end_line = end_line
        self.start_column = start_column
        self.end_column = end_column
        self.flag = flag
        self.tag_history = tag_history

def uniform(warnings, tool, rules):
    uni_warnings = []
    for warning in warnings:
        trace_base = warning.trace[0]

        rule_id = trace_base.data['ruleId']
        try:
            rule = rules.loc[[rule_id]]
        except KeyError:
            continue
        if rule.isnull().values.all():
            continue

        wtype = rule_id
        cwe = rule['cwe'].values[0]
        message = trace_base.message()
        file = trace_base.uri()
        start_line = trace_base.start_line()
        end_line = trace_base.end_line()
        start_column = trace_base.start_column()
        end_column = trace_base.end_column()
        flag = False
        tag_history = [
            Trace(
                trace.uri(),
                trace.start_line()
            ) for trace in warning.trace[1:]
        ]

        uni_warnings.append(Warning(
            wtype,
            cwe,
            message,
            file,
            start_line,
            end_line,
            start_column,
            end_column,
            flag,
            tag_history
        ))
    return uni_warnings

import json

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Trace):
            return obj.__dict__
        if isinstance(obj, Warning):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)