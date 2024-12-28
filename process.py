from operator import truediv
from optparse import check_choice
import os
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
    "commons-io": "JAVA11_HOME",
    "commons-lang": "JAVA11_HOME",   
    "opennlp": "JAVA17_HOME",
    "pdfbox": "JAVA8_HOME",
    "ratis": "JAVA8_HOME"
}

# infer
def infer_run():
    subprocess.run(
        [
            "infer", "run",
            "--", "mvn", "clean", "install",
            "-Drat.skip=true", "-Dmaven.test.skip=true", "-Dmdep.analyze.skip=true", "-Dskip=true", "-Danimal.sniffer.skip=true"
        ],
        check=True,
        capture_output=not VERBOSE,
    )

def compare_reports_infer(config, repo: str, base_report, compare_report, output_dir, cwd):
    subprocess.run([
        "infer", "reportdiff",
        "--report-previous", os.path.join(cwd, str(base_report)),
        "--report-current", os.path.join(cwd, str(compare_report)),
    ], check=True, capture_output=not VERBOSE)

# spotbugs
def spotbugs_run():
    p1 = subprocess.Popen(["find", ".", "-name", "*class", "!", "-path", "*/opennlp-distr/*"], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["spotbugs", "-textui", "-xargs", "-sarif=spotbugs.sarif"], stdin=p1.stdout, stdout=subprocess.PIPE)

    p1.stdout.close()
    p2.communicate()

def compare_reports_spots_bugs():
    # TODO
    os.abort()

# codeql
def codeql_run():
    # Create the database
    subprocess.run(
        [
            "codeql", "database", "create", "java-database", 
            "--language=java", "--source-root=.", "--no-run-unnecessary-builds", "--overwrite"
        ],
        check=True,
        capture_output=not VERBOSE,
    )

    subprocess.run(
        [
            "codeql", "database", "analyze", "java-database",
            "--format=sarif-latest", "--output=codeql.sarif",
            "java-security-and-quality.qls"
        ],
        check=True,
        capture_output=not VERBOSE,
    )

    # Remove the database
    subprocess.run(
        [
            "rm", "-rf", "java-database" 
        ],
        check = True,
        capture_output=not VERBOSE,
    )

def compare_reports_codeql():
    # TODO
    os.abort()

# pmd
def pmd_run():
    subprocess.run(
        [
            "pmd", "check", "-d", ".", "-f", "sarif", "-r", "pmd.sarif", "-R", "rulesets/java/quickstart.xml"
        ],
        check=True,
        capture_output=not VERBOSE,
    )

def compare_reports_pmd():
    # TODO
    os.abort()

# semgrep
def semgrep_run():
    subprocess.run(
        [
            "semgrep", "scan", ".", "--sarif-output=semgrep.sarif"
        ],
        check=True,
        capture_output=not VERBOSE,
    )

def compare_reports_semgrep():
    # TODO
    os.abort()

COMPARE_TOOL_FUNCTIONS = {
    "infer": compare_reports_infer,
    "spotbugs": compare_reports_spots_bugs,
    "codeql": compare_reports_codeql,
    "pmd": compare_reports_pmd,
    "semgrep": compare_reports_semgrep,
}

TOOL_RUNNERS = {
    "infer": infer_run,
    "spotbugs": spotbugs_run,
    "codeql": codeql_run,
    "pmd": pmd_run,
    "semgrep": semgrep_run,
}

def compare_tool_reports(tool: str, repo: str, base_report, compare_report, output_dir, cwd):
    config = TOOL_SETTINGS[tool]
    compare_func = COMPARE_TOOL_FUNCTIONS.get(tool)
    if not compare_func:
        raise ValueError(f"Unknown tool: {tool}")
    compare_func(config, repo, base_report, compare_report, output_dir, cwd)


def compare_reports(tool: str, repo: str, base_tag: str, compare_tag: str) -> str:
    config = TOOL_SETTINGS[tool]
    base_path = Path(f"./repos/{tool}/{repo}/{base_tag}").glob(f"*/{config['report_dir']}/{config['report_file']}")
    compare_path = Path(f"./repos/{tool}/{repo}/{compare_tag}").glob(f"*/{config['report_dir']}/{config['report_file']}")
    base_report = next(base_path)
    compare_report = next(compare_path)
    output_dir = Path(f"./reports/{repo}/{compare_tag}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(output_dir.resolve())
    compare_tool_reports(tool, repo, base_report, compare_report, output_dir, cwd)
    os.chdir(cwd)
    return str(output_dir / f"{config['report_dir']}" / "differential" / config['fixed_file'])

def get_warning_key(warning):
    """Create a unique key for a warning based on its identifying attributes"""
    return (
        warning.get('bug_type'),
        warning.get('file'),
        warning.get('line'),
        warning.get('column'),
        warning.get('hash')
    )

def process_reports(tool: str, repo: str, tags: List[str]):
    base_tag = tags[0]  # tag_1
    fixed_reports = []
    
    for tag in tags[1:]:
        try:
            fixed_json = compare_reports(tool, repo, base_tag, tag)
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

def set_java_home(repo: str):
    java_home = JAVA_HOMES.get(repo)
    if not java_home:
        raise ValueError(f"Unknown repo: {repo}")
    os.environ["JAVA_HOME"] = os.getenv(java_home)

def get_sorted_tags(tags: List[str]) -> List[str]:
    return sorted(tags, key=lambda tag: int(tag.split("_")[-1]))

@app.command()
def main(
    repos: List[str] = typer.Option([], "--repos", "-r", help="List of repos to process"),
    ignore_repos: List[str] = typer.Option([], "--ignore", "-i", help="List of repos to exclude"),
    included_tags: List[int] = typer.Option([], "--tags", "-t", help="List of tags to include"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    analyze: bool = typer.Option(False, "--analyze", "-a"),
    report: bool = typer.Option(False, "--report"),
    tool: str = typer.Option("infer", "--tool", help="Analysis tool to use"),
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
            process_reports(tool, repo, tags)
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
                if tool in TOOL_RUNNERS:
                    TOOL_RUNNERS[tool]()
                else:
                    raise ValueError(f"Unknown tool: {tool}")
                print(f"{tool} run successfully")
            except subprocess.CalledProcessError as e:
                if VERBOSE:
                    print(f"Error: {e}")
                error_list.append(repo_path)
            os.chdir(original_wd)
        print(f"Error list: {error_list}")


if __name__ == "__main__":
    app()