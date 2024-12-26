from math import fabs
import os
import requests
import tarfile
from datetime import datetime

proxies = {
    "http": "http://localhost:7890",
    "https": "http://localhost:7890",
}

# proxies = {

# }

def get_tags(repo_url: str):
    user, repo = repo_url.rstrip('/').split('/')[-2:]
    api_url = f"https://api.github.com/repos/{user}/{repo}/tags"
    tags = []

    github_token = os.getenv("GITHUB_TOKEN")
    headers = {'Authorization': f'token {github_token}'} if github_token else {}

    response = requests.get(f"{api_url}", headers=headers, proxies=proxies)
    response.raise_for_status()
    data = response.json()

    for tag in data:
        if len(tags) >= 10:
            break
        tag_name = tag['name']
        commit_url = tag['commit']['url']
        commit_response = requests.get(commit_url, headers=headers, proxies=proxies)
        try:
            commit_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error: {e}")
            continue

        commit_data = commit_response.json()
        tag_date = commit_data['commit']['committer']['date']
        if datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ") > datetime.strptime("2023-01-01", "%Y-%m-%d"):
            print(f"Tag {tag_name} created at {tag_date}")
            tags.append((tag_name, tag_date))

    tags = sorted(tags, key=lambda x: datetime.strptime(x[1], "%Y-%m-%dT%H:%M:%SZ"))
    print(tags)
    return tags

def download_and_extract_tag(repo_url: str, tag_name: str, tag_num: int):
    user, repo = repo_url.rstrip('/').split('/')[-2:]
    extract_dir = os.path.join(repo, f"tag_{tag_num}")
    # if dir exist, pass
    if os.path.exists(extract_dir):
        print(f"pass tag_{tag_num}")
        return
    tarball_url = f"https://github.com/{user}/{repo}/archive/refs/tags/{tag_name}.tar.gz"
    print(f"Downloading {tag_name} from {tarball_url}...")

    response = requests.get(tarball_url)
    response.raise_for_status()
    
    compressed_file = os.path.join(repo, ".tar.gz")
    with open(compressed_file, 'wb') as f:
        f.write(response.content)
    print(f"Extracting {compressed_file}...")
    with tarfile.open(compressed_file, "r:gz") as tar:
        tar.extractall(path=extract_dir)
    os.remove(compressed_file)

def main(repo_url: str):
    print(f"Processing repository: {repo_url}")
    tags = get_tags(repo_url)
    for i in range(len(tags)):
        download_and_extract_tag(repo_url, tags[i][0], i + 1)

if __name__ == "__main__":
    repo_url = input("Enter GitHub repository URL (e.g., https://github.com/owner/repo): ")
    main(repo_url)
