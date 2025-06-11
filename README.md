# AmazonFBA_AI_Agent

This repository contains utilities for managing the "Amazon FBA AI Agent" project. 

## GitHub Project automation

`create_project.py` creates or updates a GitHub Projects v2 board named **"Amazon FBA AI Agent - Roadmap"** under your GitHub account and links it to this repository. The script requires a personal access token with `repo`, `project`, and `write:discussion` scopes.

### Usage

1. Set a `GITHUB_TOKEN` environment variable containing your Personal Access Token.
2. Run the script:
   ```bash
   python create_project.py
   ```
   The script prints the project ID and confirms it was linked and populated with default tasks.
