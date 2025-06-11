import os
import json
from urllib import request

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    raise SystemExit("GITHUB_TOKEN environment variable not set")

API_URL = "https://api.github.com/graphql"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

def run_query(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = request.Request(API_URL, data=payload, headers=HEADERS)
    with request.urlopen(req) as resp:
        if resp.status != 200:
            raise Exception(f"Query failed with code {resp.status}: {resp.read().decode()}")
        body = resp.read().decode()
    data = json.loads(body)
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    return data["data"]

def get_viewer_info():
    query = """
    query { viewer { id login } }
    """
    data = run_query(query)
    return data["viewer"]

def find_project(owner_id, title):
    query = """
    query($ownerId: ID!, $title: String!) {
      node(id: $ownerId) {
        ... on User {
          projectsV2(first: 50, query: $title) {
            nodes { id title }
          }
        }
      }
    }
    """
    data = run_query(query, {"ownerId": owner_id, "title": title})
    projects = data["node"]["projectsV2"]["nodes"]
    for p in projects:
        if p["title"] == title:
            return p["id"]
    return None

def create_project(owner_id, title):
    mutation = """
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {ownerId: $ownerId, title: $title}) {
        projectV2 { id title }
      }
    }
    """
    data = run_query(mutation, {"ownerId": owner_id, "title": title})
    return data["createProjectV2"]["projectV2"]["id"]

def add_field(project_id, name, options):
    mutation = """
    mutation($projectId: ID!, $name: String!, $options: [ProjectV2SingleSelectFieldOptionInput!]) {
      createProjectV2Field(input: {projectId: $projectId, dataType: SINGLE_SELECT, name: $name, singleSelectOptions: $options}) {
        projectV2Field { id }
      }
    }
    """
    variables = {
        "projectId": project_id,
        "name": name,
        "options": [{"name": opt} for opt in options],
    }
    run_query(mutation, variables)

def link_repo(project_id, owner, name):
    query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) { id }
    }
    """
    repo_data = run_query(query, {"owner": owner, "name": name})
    repo_id = repo_data["repository"]["id"]

    mutation = """
    mutation($projectId: ID!, $repoId: ID!) {
      linkProjectV2ToRepository(input: {projectId: $projectId, repositoryId: $repoId}) {
        projectV2 { id }
      }
    }
    """
    run_query(mutation, {"projectId": project_id, "repoId": repo_id})

def add_draft_item(project_id, title, body=""):
    mutation = """
    mutation($projectId: ID!, $title: String!, $body: String!) {
      addProjectV2DraftIssue(input: {projectId: $projectId, title: $title, body: $body}) {
        projectItem { id }
      }
    }
    """
    run_query(mutation, {"projectId": project_id, "title": title, "body": body})

def main():
    viewer = get_viewer_info()
    owner_id = viewer["id"]
    title = "Amazon FBA AI Agent - Roadmap"

    project_id = find_project(owner_id, title)
    if project_id:
        print(f"Project already exists with ID: {project_id}")
    else:
        project_id = create_project(owner_id, title)
        print(f"Created project '{title}' with ID: {project_id}")

        add_field(project_id, "Status", ["Backlog", "In Progress", "Review", "Done"])
        print("Added Status field with workflow options.")

        link_repo(project_id, "miguelsanchezvelo", "AmazonFBA_AI_Agent")
        print("Linked project to repository 'miguelsanchezvelo/AmazonFBA_AI_Agent'.")

        tasks = [
            "Implement product discovery module",
            "Create market analysis script",
            "Build profitability estimator",
            "Design and implement Dev Agent",
        ]
        for task in tasks:
            add_draft_item(project_id, task)
        print("Initialized project with default tasks.")

    print(f"Project setup complete. ID: {project_id}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
