# Notion to GitHub Pages Automation Tool

A powerful Python CLI tool that automates the conversion and deployment of Notion pages to GitHub Pages, streamlining content publishing workflows for developers and content creators.

## Project Overview

This project solves the challenge of manually exporting Notion content and deploying it to static sites. As a developer, I recognized the inefficiency in the traditional workflow: writing in Notion, exporting as Markdown, downloading images, and manually uploading to GitHub Pages. This tool automates the entire pipeline, from API fetching to git commits.

### Key Features
- **Async Notion API Integration**: Efficiently fetches page content using Notion's REST API with proper error handling
- **Intelligent Block Conversion**: Converts Notion blocks (headings, lists, code, equations, images) to clean Markdown
- **Image Management**: Automatically downloads and relocates images with URL rewriting for static hosting
- **Git Automation**: Optional auto-commit and push to GitHub Pages repositories
- **CLI-Driven Workflow**: User-friendly command-line interface with configuration management
- **Type-Safe Architecture**: Built with Pydantic for robust data validation and error prevention

## Architecture & Design

### Thought Process as a Developer

When approaching this problem, I focused on modularity and scalability:

1. **API Layer**: Started with a robust Notion client handling authentication, pagination, and error responses
2. **Data Modeling**: Used Pydantic to create type-safe models for Notion's complex JSON structures
3. **Processing Pipeline**: Designed a three-stage pipeline: fetch → parse → convert → deploy
4. **CLI Interface**: Built an intuitive CLI with Click, supporting both page IDs and friendly names
5. **Deployment Automation**: Integrated git operations for seamless publishing workflows

### Core Components

- **`NotionClient`**: Async HTTP client with comprehensive error handling for Notion API v1
- **`BlockParser`**: Filters and structures Notion blocks into processable content
- **`MarkdownConverter`**: Handles rich text annotations, block types, and formatting
- **`Deployer`**: Orchestrates the full deployment pipeline with logging and git integration
- **`ConfigManager`**: Manages deployment settings and page mappings

## Technical Implementation

### Technologies Used
- **Python 3.12**: Modern Python with type hints and async/await
- **httpx**: Async HTTP client for API requests
- **Pydantic**: Data validation and settings management
- **Click**: Command-line interface framework
- **GitPython/subprocess**: Git automation for deployment

### Key Technical Decisions

- **Async Architecture**: Chose async programming for non-blocking I/O operations, crucial for API calls and file downloads
- **Pydantic Models**: Ensured type safety and automatic validation of Notion API responses
- **Modular Design**: Separated concerns into distinct classes for maintainability and testing
- **Error Handling**: Implemented custom exception hierarchy for different Notion API error scenarios
- **Configuration Management**: JSON-based config with environment variable support for flexibility

## Installation & Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/notion-to-gh-pages.git
cd notion-to-gh-pages

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export NOTION_API_TOKEN="your_notion_integration_token"
```

## Configuration

Create a `deploy-config.json` file:

```json
{
  "pages": {
    "my-article": "notion_page_id_here"
  },
  "settings": {
    "auto_commit": true,
    "download_images": true,
    "verbose": false,
    "output_dir": "../your-github-pages-repo/content/posts"
  }
}
```

## Usage

### Basic Deployment

```bash
# Deploy by page name
python main.py deploy --page my-article

# Deploy by Notion page ID
python main.py deploy --page-id 1234567890abcdef

# Deploy with auto-commit
python main.py deploy --page my-article --auto-commit
```

### Advanced Options

```bash
# Verbose output for debugging
python main.py deploy --page my-article --verbose

# Skip image downloads
python main.py deploy --page my-article --no-download-images

# Custom output directory
python main.py deploy --page my-article --output-dir /path/to/output
```

### Management Commands

```bash
# List configured pages
python main.py list-pages

# Remove a deployed page
python main.py remove --page my-article --auto-commit
```

## Deployment Workflow

1. **Fetch**: Retrieves all blocks from the specified Notion page using pagination
2. **Parse**: Filters processable blocks and extracts structured content
3. **Convert**: Transforms Notion blocks to Markdown with proper formatting
4. **Download**: Fetches images and updates URLs for static hosting
5. **Save**: Writes Markdown files with Hugo/Jekyll frontmatter
6. **Index**: Updates `posts-index.json` for dynamic site generation
7. **Commit**: Optionally commits and pushes changes to GitHub Pages

## Takeaways

This project showcases expertise in:

- **API Integration**: Building robust clients for third-party APIs with error handling
- **Async Programming**: Leveraging Python's asyncio for concurrent operations
- **Data Processing**: Parsing complex JSON structures and converting between formats
- **CLI Development**: Creating user-friendly command-line tools with Click
- **Automation**: Integrating with git and external tools for CI/CD-like workflows
- **Type Safety**: Using modern Python typing and validation libraries
- **Project Architecture**: Designing modular, maintainable software systems

## Future Enhancements

- Webhook integration for automatic sync with Notion
- Support for nested block structures and advanced Notion features
- Batch processing for multiple pages
- Integration with other static site generators
- Content diffing and incremental updates

## 📄 License

MIT License - feel free to use and modify for your own projects.

---

*Built with ❤️ by a passionate developer automating content workflows*
