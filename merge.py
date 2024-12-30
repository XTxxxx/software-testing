import json
from uniform import Encoder
import os
from tqdm import tqdm

repos = ['commons-io', 'commons-lang', 'opennlp', 'pdfbox', 'ratis']
tools = ['codeql', 'pmd', 'spotbugs', 'semgrep']

def get_report(repo, tool):
    report_path = f'reports/{tool}/{repo}/warnings.json'
    with open(report_path, 'r') as f:
        return json.load(f)

def same_warning(war1, war2):
    same = \
        war1["file"].split("/")[-1] == war2["file"].split("/")[-1] and \
        war1["start_line"] == war2["start_line"] and \
        war1["end_line"] == war2["end_line"]
    return same

if __name__ == "__main__":
    result_path = 'merged'
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    for repo in tqdm(repos, position=0, desc='Processing repos'):
        warnings = []
        for tool in tqdm(tools, position=1, desc='Processing tools', leave=False):
            report = get_report(repo, tool)
            cur_warnings = []
            for warning in report:
                hasSame = False
                for war, dup in warnings:
                    if same_warning(warning, war):
                        dup += 1
                        hasSame = True
                        if dup == 3:
                            warning["flag"] = True
                        break
                if not hasSame:
                    cur_warnings.append((warning, 1))
            warnings += cur_warnings
        print(f"{repo}: {len(warnings)}")
        result, _ = zip(*warnings)
        with open(f"merged/{repo}.json", "w") as f:
            json.dump(result, f, cls=Encoder, indent=2)
