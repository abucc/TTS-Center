#!/bin/bash

# Awesome-TTS GitHub Deployment Script
# This script will initialize the repository and push to GitHub

echo "🚀 Deploying Awesome-TTS to GitHub..."
echo "======================================"

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "📁 Git repository already exists"
fi

# Set main branch
echo "🌿 Setting main branch..."
git branch -M main

# Add all files
echo "📝 Adding all files to Git..."
git add .

# Check if there are any changes to commit
if git diff --staged --quiet; then
    echo "⚠️  No changes to commit"
else
    # Commit changes
    echo "💾 Committing changes..."
    git commit -m "🎉 Initial release of Awesome-TTS unified gateway

- Complete unified TTS gateway with 5 providers
- Kokoro ONNX, ChatterboxTTS, OpenAI Edge TTS, Streamlabs TTS
- Docker Compose deployment ready
- Production nginx configuration
- Comprehensive documentation and guides
- Web interface and REST API
- Redis caching and health monitoring"
    echo "✅ Changes committed"
fi

# Check if remote origin exists
if git remote get-url origin &> /dev/null; then
    echo "🔗 Remote origin already configured"
    
    # Push to existing remote
    echo "⬆️  Pushing to GitHub..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pushed to GitHub!"
        echo ""
        echo "🎉 Deployment Complete!"
        echo "Your Awesome-TTS repository is now live on GitHub!"
    else
        echo "❌ Failed to push to GitHub"
        echo "Please check your remote URL and permissions"
    fi
else
    echo "🔗 No remote origin configured"
    echo ""
    echo "📋 Next steps to complete deployment:"
    echo "1. Create a new repository on GitHub named 'Awesome-TTS'"
    echo "2. Run one of these commands:"
    echo ""
    echo "   For HTTPS:"
    echo "   git remote add origin https://github.com/isaacgounton/Awesome-TTS.git"
    echo "   git push -u origin main"
    echo ""
    echo "   For SSH:"
    echo "   git remote add origin git@github.com:isaacgounton/Awesome-TTS.git"
    echo "   git push -u origin main"
    echo ""
    echo "Replace isaacgounton with your actual GitHub username"
fi

echo ""
echo "📊 Repository Statistics:"
echo "========================"
echo "Total files: $(find . -type f -not -path './.git/*' | wc -l)"
echo "Docker services: 5 (Kokoro, Chatterbox, OpenAI Edge, Streamlabs, Gateway)"
echo "Documentation files: $(ls *.md 2>/dev/null | wc -l)"
echo "Voice configurations: $(ls voices/*.json 2>/dev/null | wc -l)"
echo ""
echo "🌟 Don't forget to:"
echo "- Add topics/tags to your GitHub repository"
echo "- Enable GitHub Pages for documentation (optional)"
echo "- Set up GitHub Actions for CI/CD (optional)"
echo "- Star your own repository! ⭐"
