
import os
import glob
import json
import re
import pandas as pd

class RuleEntry:
    def __init__(
        self,
        tool: str,
        id: str,
        description: str,
        cwe: str = "CWE-",
    ):
        self.tool = tool
        self.id = id
        self.description = description
        self.cwe = cwe

tools = ['codeql', 'pmd', 'spotbugs', 'semgrep']

def load_raw_rule(tool):
    path = f'repos/commons-io/tag_1/*/{tool}.sarif'
    sarif_file = glob.glob(path)
    assert len(sarif_file) == 1
    sarif_path = sarif_file[0]
    with open(sarif_path, 'r', encoding='UTF-8') as f:
        data = json.load(f)
        rules = data['runs'][0]['tool']['driver']['rules']
    return rules

def uni_codeql(all_rules):
    rules = load_raw_rule('codeql')
    for rule in rules:
        all_rules['tool'].append('codeql')
        all_rules['id'].append(rule['id'])
        cwe = 'CWE-unknown'
        for tag in rule['properties']['tags']:
            matchObj = re.search(r'\d+', tag)
            if matchObj:
                cwe = 'CWE-' + matchObj.group()
                break
        all_rules['cwe'].append(cwe)

def uni_pmd(all_rules):
    rules = load_raw_rule('pmd')
    for rule in rules:
        all_rules['tool'].append('pmd')
        all_rules['id'].append(rule['id'])
        all_rules['cwe'].append('CWE-unknown')

def uni_spotbugs(all_rules):
    rules = load_raw_rule('spotbugs')
    for rule in rules:
        all_rules['tool'].append('spotbugs')
        all_rules['id'].append(rule['id'])
        cwe = 'CWE-unknown'
        if rule.get('relationships'):
            cwe = 'CWE-' + rule['relationships'][0]['target']['id']
        all_rules['cwe'].append(cwe)

def uni_semgrep(all_rules):
    rules = load_raw_rule('semgrep')
    for rule in rules:
        all_rules['tool'].append('semgrep')
        all_rules['id'].append(rule['id'])
        cwe = 'CWE-unknown'
        for tag in rule['properties']['tags']:
            matchObj = re.search(r'CWE-\d+', tag)
            if matchObj:
                cwe = matchObj.group()
                break
        all_rules['cwe'].append(cwe)

RULE_FUNC = {
    'codeql': uni_codeql,
    'pmd': uni_pmd,
    'spotbugs': uni_spotbugs,
    'semgrep': uni_semgrep,
}

if __name__ == '__main__':
    all_rules = {}
    all_rules['tool'], all_rules['id'], all_rules['cwe'] = [], [], []
    for tool in tools:
        RULE_FUNC[tool](all_rules)

    save_path = 'rules.csv'
    df = pd.DataFrame(all_rules)
    df.drop_duplicates(subset=['id'], keep='first', inplace=True)
    df.to_csv(save_path, index=False)
    