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
    echo "✓ Git initialized with 'main' branch"
else
    # Check if we're on a branch, if not we might be in detached HEAD
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ "$CURRENT_BRANCH" = "HEAD" ]; then
        echo "Creating main branch..."
        git checkout -b main
    fi
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

# Check if there are any changes to commit
if git diff-index --quiet HEAD -- 2>/dev/null; then
    echo ""
    echo "No changes to commit"
    exit 0
fi

# Commit
echo ""
echo "Committing with message: '$COMMIT_MESSAGE'"
git commit -m "$COMMIT_MESSAGE"

# Check if commit was successful
if [ $? -eq 0 ] || [ $? -eq 1 ]; then
    # Get current branch name
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
    
    echo ""
    echo "Pushing to GitHub on branch: $CURRENT_BRANCH..."
    git push -u origin $CURRENT_BRANCH
    
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
