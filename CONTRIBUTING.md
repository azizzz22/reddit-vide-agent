# Contributing to Reddit Video Agent

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs
1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/reddit-video-agent/issues)
2. If not, create a new issue with:
   - Clear title
   - Detailed description
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Python version)
   - Error logs/screenshots

### Suggesting Features
1. Open an issue with tag `enhancement`
2. Describe the feature and use case
3. Explain why it would be valuable

### Code Contributions

#### Setup Development Environment
```bash
# Fork and clone
git clone https://github.com/yourusername/reddit-video-agent.git
cd reddit-video-agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create feature branch
git checkout -b feature/your-feature-name
```

#### Code Style
- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions/classes
- Keep functions focused and small

#### Testing
- Test your changes thoroughly
- Include example Reddit URLs that work
- Verify on different content types (video, text, image posts)

#### Commit Messages
```
feat: Add TikTok-style word highlighting
fix: Correct caption synchronization timing
docs: Update README with new features
refactor: Simplify timeline building logic
```

#### Pull Request Process
1. Update README.md if needed
2. Add your changes to CHANGELOG.md
3. Ensure all tests pass
4. Create PR with clear description
5. Link related issues

## Development Guidelines

### Agent Architecture
- Each agent should have single responsibility
- Use async/await for I/O operations
- Handle errors gracefully with fallbacks
- Log important steps for debugging

### Adding New Agents
1. Create in `reddit_video_agent/agents/`
2. Inherit from `BaseAgent`
3. Implement `async def execute()`
4. Register in `agents/__init__.py`
5. Update Director workflow

### Performance
- Optimize for speed (users wait for videos)
- Cache expensive operations
- Use multiprocessing where applicable
- Profile before optimizing

## Community

- Be respectful and constructive
- Help others in issues/discussions
- Share your generated videos!
- Suggest improvements

## Questions?

Open a discussion or issue - we're here to help! 🚀
