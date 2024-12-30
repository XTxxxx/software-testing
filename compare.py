import json
import os
import re
import glob
import pandas as pd
from tqdm import tqdm
from warning import to_warning
from uniform import uniform, Encoder

repos = ['commons-io', 'commons-lang', 'opennlp', 'pdfbox', 'ratis']
tools = ['codeql', 'pmd', 'spotbugs', 'semgrep']

# repos = ['commons-io']
# tools = ['spotbugs']

class SarifData:
    def __init__(self, path: str, tag: str, tool: str):
        self.path = path
        self.tag = int(re.findall(r'\d+', tag)[0])
        self.tool = tool

        with open(path, 'r', encoding='UTF-8') as f:
            data = json.load(f)
            self.results = data['runs'][0]['results']
            self.rules = data['runs'][0]['tool']['driver']['rules']

""" Load SARIF of all tags for a given repo and tool """
def load_sarifs(repo, tool):
    sarifs = []

    base_path = f'repos/{repo}'
    tags = os.listdir(base_path)
    assert len(tags) > 0 # at least one tag per repo

    for tag in tags:
        sarif_file = glob.glob(f'{base_path}/{tag}/*/{tool}.sarif')
        assert len(sarif_file) == 1 # only one sarif file per tool per tag
        sarif_path = sarif_file[0]
        sarifs.append(SarifData(sarif_path, tag, tool))

    sarifs.sort(key=lambda x: x.tag)
    return sarifs

def get_real_warnings(sarifs):
    real_warnings = []
    base_results = sarifs[0].results
    rules = sarifs[0].rules
    for base_result in tqdm(base_results, desc='Processing warnings'):
        warning = to_warning(base_result)
        # scan all tags
        for sarif in sarifs[1:]:
            has_trace = False
            for result in sarif.results:
                if warning.try_add_trace(result):
                    has_trace = True
                    break
            if not has_trace:
                real_warnings.append(warning)
                break
    return real_warnings

if __name__ == '__main__':
    rules = pd.read_csv('rules.csv')
    rules.set_index('id', inplace=True)
    for repo in repos:
        for tool in tools:
            sarifs = load_sarifs(repo, tool)
            print("Processing ", repo, " ", tool)
            # compare warnings
            try:
                real_warnings = get_real_warnings(sarifs)
            except Exception as e:
                print(f'Error in {repo} {tool}: {e}')
                continue
            print(f'{repo} {tool}: {len(sarifs[0].results)} warnings, {len(real_warnings)} real warnings')

            # save real warnings
            warning_dir_path = f'reports/{tool}/{repo}/'
            os.makedirs(warning_dir_path, exist_ok=True)
            with open(f'{warning_dir_path}warnings.json', 'w') as f:
                uni_warnings = uniform(real_warnings, tool, rules)
                json.dump(uni_warnings, f, cls=Encoder, indent=2)
