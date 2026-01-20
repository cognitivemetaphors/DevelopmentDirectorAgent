#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo ".env file not found!"
    exit 1
fi

# Tell the GitHub CLI to use your token from the .env file
export GH_TOKEN=$GITHUB_TOKEN

REPO_NAME="DevelopmentDirectorAgent"

# Create the repo using the token for authentication
# --public makes it visible; use --private for a private repo
gh repo create $REPO_NAME --public --source=. --remote=origin --push

echo "Successfully authenticated and pushed $REPO_NAME to GitHub."
