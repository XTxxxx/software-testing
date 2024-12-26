import os
from readline import append_history_file
import subprocess
from typing import List, Dict, Any
import typer
import json
from pathlib import Path

app = typer.Typer()
VERBOSE = False


""" repos are saved in "./repos" """
DEFAULT_REPOS = [
    "commons-io",
    "commons-lang",
    "opennlp",
    "pdfbox",
    "ratis"
]
JAVA_HOMES = {
    "commons-io": "JAVA8_HOME",
    "commons-lang": "JAVA11_HOME",   
    "opennlp": "JAVA17_HOME",
    "pdfbox": "JAVA8_HOME",
    "ratis": "JAVA8_HOME"
}

class BugReport:
    def __init__(self, bug_type: str, qualifier: str, severity: str, line: int, column: int, procedure: str, procedure_start_line: int, file: str, bug_trace: List[Dict[str, Any]], key: str, node_key: str, hash: str, bug_type_hum: str):
        self.bug_type = bug_type
        self.qualifier = qualifier
        self.severity = severity
        self.line = line
        self.column = column
        self.procedure = procedure
        self.procedure_start_line = procedure_start_line
        self.file = file
        self.bug_trace = bug_trace
        self.key = key
        self.node_key = node_key
        self.hash = hash
        self.bug_type_hum = bug_type_hum


"""Sort tags"""
def get_sorted_tags(tags: List[str]) -> List[str]:
    return sorted(tags, key=lambda x: int(x.split("_")[1]))

def set_java_home(repo: str):
    java_home = JAVA_HOMES[repo]
    os.environ["JAVA_HOME"] = os.getenv(java_home)

def compare_reports(repo: str, base_tag: str, compare_tag: str) -> str:
    base_path = Path(f"./repos/{repo}/{base_tag}").glob("*/infer-out/report.json")
    compare_path = Path(f"./repos/{repo}/{compare_tag}").glob("*/infer-out/report.json")
    
    base_report = next(base_path)
    compare_report = next(compare_path)
    
    output_dir = Path(f"./reports/{repo}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir / f"{compare_tag}"
    output_dir.mkdir(parents=True, exist_ok=True)

    cwd = os.getcwd()
    os.chdir(output_dir.resolve())
    
    subprocess.run([
        "infer", "reportdiff",
        "--report-previous", os.path.join(cwd, str(base_report)),
        "--report-current", os.path.join(cwd, str(compare_report)),
    ], check=True, capture_output=not VERBOSE)
    
    os.chdir(cwd)
    return str(output_dir / "infer-out" / "differential" / "fixed.json")

def get_warning_key(warning):
    """Create a unique key for a warning based on its identifying attributes"""
    return (
        warning.get('bug_type'),
        warning.get('file'),
        warning.get('line'),
        warning.get('column'),
        warning.get('hash')
    )

def process_reports(repo: str, tags: List[str]):
    base_tag = tags[0]  # tag_1
    fixed_reports = []
    
    for tag in tags[1:]:
        try:
            fixed_json = compare_reports(repo, base_tag, tag)
            fixed_reports.append(fixed_json)
        except Exception as e:
            if VERBOSE:
                print(f"Error comparing reports for {repo} {tag}: {e}")
    
    # Combine all fixed reports with duplicate handling
    combined_warnings = []
    seen_warnings = set()
    
    for report in fixed_reports:
        try:
            with open(report) as f:
                data = json.load(f)
                for warning in data:
                    warning_key = get_warning_key(warning)
                    if warning_key not in seen_warnings:
                        seen_warnings.add(warning_key)
                        combined_warnings.append(warning)
        except Exception as e:
            if VERBOSE:
                print(f"Error processing report {report}: {e}")
    
    # Save combined warnings
    output_path = Path(f"./reports/{repo}/warnings.json")
    with open(output_path, "w") as f:
        json.dump(combined_warnings, f, indent=2)

@app.command()
def main(
    repos: List[str] = typer.Option([], "--repos", "-r", help="List of repos to process"),
    ignore_repos: List[str] = typer.Option([], "--ignore", "-i", help="List of repos to exclude"),
    included_tags: List[int] = typer.Option([], "--tags", "-t", help="List of tags to include"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    analyze: bool = typer.Option(False, "--analyze", "-a"),
    report: bool = typer.Option(False, "--report"),
    ):
    global VERBOSE
    VERBOSE = verbose
    if len(repos) == 0:
        repos = DEFAULT_REPOS
    if len(ignore_repos) > 0:
        repos = [repo for repo in repos if repo not in ignore_repos]
    if len(included_tags) > 0:
        included_tags = [f"tag_{tag}" for tag in included_tags]

    # Choose a repo in repos
    for repo in repos:
        set_java_home(repo)
        if VERBOSE:
            print(f"Set JAVA_HOME to {os.getenv('JAVA_HOME')}")
        tags = next(os.walk(f"./repos/{repo}"))[1]
        tags = get_sorted_tags(tags)
        
        if report:
            process_reports(repo, tags)
            continue

        if VERBOSE:
            print(tags)
        error_list = []
        for tag in tags:
            if len(included_tags) > 0 and tag not in included_tags:
                continue
            tag_path = os.path.join("repos", repo, tag)
            tag_walked = os.walk(tag_path)
            root, dirname, _ = next(tag_walked)
            dirname = dirname[0]
            repo_path = os.path.join(root, dirname)
            original_wd = os.getcwd()
            os.chdir(repo_path)
            try:
                print(f"Processing {repo_path}")
                # Run the script
                subprocess.run(["infer", "run", "--", "mvn", "clean", "install",
                                "-Drat.skip=true", "-Dmaven.test.skip=true", "-Dmdep.analyze.skip=true", "-Dskip=true", "-Danimal.sniffer.skip=true"], 
                                check=True,
                                capture_output=not VERBOSE,
                )

                print("Infer run successfully")
            except subprocess.CalledProcessError as e:
                if VERBOSE:
                    print(f"Error: {e}")
                error_list.append(repo_path)
            os.chdir(original_wd)
        print(f"Error list: {error_list}")


if __name__ == "__main__":
    app()