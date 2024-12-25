from math import fabs
import os
import requests
import tarfile
from datetime import datetime

def get_tags(repo_url):
    user, repo = repo_url.rstrip('/').split('/')[-2:]
    api_url = f"https://api.github.com/repos/{user}/{repo}/tags"
    tags = []
    page = 1

    github_token = os.getenv("GITHUB_TOKEN")
    headers = {'Authorization': f'token {github_token}'} if github_token else {}

    cont = True
    while cont:
        response = requests.get(f"{api_url}?page={page}&per_page=10", headers=headers)
        response.raise_for_status()
        data = response.json()

        if not data:
            break

        for tag in data:
            tag_name = tag['name']
            commit_url = tag['commit']['url']
            commit_response = requests.get(commit_url, headers=headers)
            commit_response.raise_for_status()
            commit_data = commit_response.json()
            tag_date = commit_data['commit']['committer']['date']
            # if tag_date is less up-to-date than 2023-01-01, break
            if datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ") < datetime.strptime("2023-01-01", "%Y-%m-%d"):
                cont = False
                break
            print(f"Tag {tag_name} created at {tag_date}")
            tags.append((tag_name, tag_date))

        page += 1

    return tags

def download_and_extract_tag(repo_url, tag_name, tag_num):
    user, repo = repo_url.rstrip('/').split('/')[-2:]
    tarball_url = f"https://github.com/{user}/{repo}/archive/refs/tags/{tag_name}.tar.gz"
    print(f"Downloading {tag_name} from {tarball_url}...")

    response = requests.get(tarball_url)
    response.raise_for_status()
    
    compressed_file = os.path.join(repo, f".tar.gz")
    extract_dir = os.path.join(repo, f"tag_{tag_num}")
    with open(compressed_file, 'wb') as f:
        f.write(response.content)
    print(f"Extracting {compressed_file}...")
    with tarfile.open(compressed_file, "r:gz") as tar:
        tar.extractall(path=extract_dir)
    os.remove(compressed_file)

def main(repo_url):
    print(f"Processing repository: {repo_url}")
    tags = get_tags(repo_url)
    for i in range(len(tags)):
        download_and_extract_tag(repo_url, tags[i][0], len(tags) - i)

if __name__ == "__main__":
    repo_url = input("Enter GitHub repository URL (e.g., https://github.com/owner/repo): ")
    main(repo_url)
