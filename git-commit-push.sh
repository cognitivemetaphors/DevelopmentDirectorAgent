#!/bin/bash

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo ".env file not found!"
    exit 1
fi

export GH_TOKEN=$GITHUB_TOKEN
REPO_NAME="DevelopmentDirectorAgent"
COMMIT_MESSAGE="${1:-Update: committed all files}"

echo "======================================"
echo "Git Commit & Push Script"
echo "======================================"

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
    git branch -M main
fi

# Check if remote exists, if not add it
if ! git remote get-url origin &>/dev/null; then
    echo "Adding remote origin..."
    USERNAME=$(gh api user --jq .login)
    git remote add origin "https://github.com/$USERNAME/$REPO_NAME.git"
else
    echo "Remote origin already configured"
fi

# Add all files
echo "Adding all files..."
git add .

# Show what will be committed
echo ""
echo "Files to be committed:"
git status --short

# Commit
echo ""
echo "Committing with message: '$COMMIT_MESSAGE'"
git commit -m "$COMMIT_MESSAGE"

# Check if commit was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "Pushing to GitHub..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ Successfully pushed to GitHub!"
        echo "View at: https://github.com/$USERNAME/$REPO_NAME"
    else
        echo ""
        echo "✗ Push failed. You may need to pull first if remote has changes."
        echo "Try: git pull origin main --rebase"
    fi
else
    echo ""
    echo "✗ Commit failed. Check if there are changes to commit."
fi
