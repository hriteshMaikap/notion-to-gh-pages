"""
Deploy Notion pages to Hugo static site.

This CLI tool fetches Notion pages, converts them to Markdown,
and deploys them to your Hugo site with proper frontmatter.

Usage:
    # Deploy by page name (from config)
    python main.py deploy --page clt
    
    # Deploy by page ID
    python main.py deploy --page-id <notion-page-id>
    
    # With auto-commit
    python main.py deploy --page clt --auto-commit
"""

import click
import os
import re
import json
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.notion_api import NotionClient
from src.notion.parser import BlockParser
from src.notion.converter import MarkdownConverter
from src.config import settings

import httpx
from urllib.parse import urlparse
import hashlib


# ============================================
# NEW: Config Manager
# ============================================

class ConfigManager:
    """Manage deployment configuration from deploy-config.json."""
    
    def __init__(self, config_path: str = "deploy-config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            return {"pages": {}, "settings": {}}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            click.echo(f"⚠️  Warning: Could not parse {self.config_path}")
            return {"pages": {}, "settings": {}}
    
    def get_page_id(self, page_name: str) -> Optional[str]:
        """Get page ID by name from config."""
        return self.config.get("pages", {}).get(page_name)
    
    def get_setting(self, key: str, default=None):
        """Get a setting value."""
        return self.config.get("settings", {}).get(key, default)
    
    def list_pages(self) -> dict:
        """List all configured pages."""
        return self.config.get("pages", {})


# ============================================
# Deployer Class (existing + git auto-commit)
# ============================================

class Deployer:
    """Handle deployment of Notion pages to Hugo site."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize deployer.
        
        Args:
            verbose: Enable verbose logging
        """
        self.verbose = verbose
        self.client = None  # Will be initialized in async context
        self.parser = None
        self.converter = MarkdownConverter()
    
    def log(self, message: str, level: str = "INFO"):
        """Log message if verbose is enabled."""
        if self.verbose:
            icon = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "ERROR": "❌",
                "WARNING": "⚠️",
                "STEP": "🔹"
            }.get(level, "ℹ️")
            click.echo(f"{icon} {message}")
    
    async def fetch_page(self, page_id: str) -> dict:
        """
        Fetch page blocks from Notion API.
        
        Args:
            page_id: Notion page ID
            
        Returns:
            Dictionary with 'results' key containing blocks
        """
        self.log(f"Fetching page: {page_id}", "STEP")
        
        # ✅ Use async method get_all_block_children
        blocks = await self.client.get_all_block_children(block_id=page_id)
        
        # ✅ Wrap in expected format (matching Notion API response)
        response = {
            "object": "list",
            "results": blocks,
            "has_more": False,
            "type": "block"
        }
        
        self.log(f"Fetched {len(blocks)} blocks", "SUCCESS")
        return response
    
    def parse_blocks(self, raw_data: dict) -> BlockParser:
        """
        Parse raw JSON into structured blocks.
        
        Args:
            raw_data: Raw JSON response from Notion
            
        Returns:
            BlockParser instance
        """
        self.log("Parsing blocks...", "STEP")
        
        parser = BlockParser.from_dict(raw_data)
        processable = parser.get_processable_blocks()
        
        self.log(f"Parsed {len(processable)} processable blocks", "SUCCESS")
        return parser
    
    def extract_title(self, parser: BlockParser) -> str:
        """
        Extract page title from first heading_1.
        
        Args:
            parser: BlockParser instance
            
        Returns:
            Page title or default
        """
        # Look for first heading_1
        heading_blocks = parser.get_blocks_by_type("heading_1")
        
        if heading_blocks:
            content = parser.get_block_content(heading_blocks[0])
            if content and content.rich_text:
                title = "".join(rt.plain_text for rt in content.rich_text)
                self.log(f"Extracted title: {title}", "SUCCESS")
                return title
        
        # Fallback to first paragraph or default
        para_blocks = parser.get_blocks_by_type("paragraph")
        if para_blocks:
            content = parser.get_block_content(para_blocks[0])
            if content and content.rich_text:
                text = "".join(rt.plain_text for rt in content.rich_text)
                title = text[:50]  # First 50 chars
                self.log(f"Using paragraph as title: {title}", "WARNING")
                return title
        
        self.log("No title found, using default", "WARNING")
        return "Untitled Page"
    
    def slugify(self, text: str) -> str:
        """
        Convert text to URL-friendly slug.
        
        Args:
            text: Text to slugify
            
        Returns:
            Slugified text
            
        Example:
            >>> slugify("Central Limit Theorem (CLT)")
            "central-limit-theorem-clt"
        """
        # Convert to lowercase
        slug = text.lower()
        
        # Remove special characters, keep alphanumeric and spaces
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        
        # Replace spaces with hyphens
        slug = re.sub(r'\s+', '-', slug)
        
        # Remove multiple hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Strip leading/trailing hyphens
        slug = slug.strip('-')
        
        return slug
    
    def generate_filename(self, title: str) -> str:
        """
        Generate Hugo-compatible filename.
        
        Format: YYYY-MM-DD-title-slug.md
        
        Args:
            title: Page title
            
        Returns:
            Filename
            
        Example:
            >>> generate_filename("Central Limit Theorem")
            "2025-11-15-central-limit-theorem.md"
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        slug = self.slugify(title)
        filename = f"{date_str}-{slug}.md"
        
        self.log(f"Generated filename: {filename}", "SUCCESS")
        return filename
    
    def generate_frontmatter(self, title: str, page_id: str) -> str:
        """
        Generate Hugo frontmatter.
        
        Args:
            title: Page title
            page_id: Notion page ID
            
        Returns:
            YAML frontmatter string
            
        Example:
            ---
            title: "Central Limit Theorem"
            date: 2025-11-15T10:30:00Z
            draft: false
            notion_page_id: "abc123"
            ---
        """
        now = datetime.now().isoformat()
        
        frontmatter = f"""---
title: "{title}"
date: {now}
draft: false
notion_page_id: "{page_id}"
---

"""
        return frontmatter
    
    def convert_to_markdown(self, parser: BlockParser) -> str:
        """
        Convert parsed blocks to Markdown.
        
        Args:
            parser: BlockParser instance
            
        Returns:
            Markdown string
        """
        self.log("Converting to Markdown...", "STEP")
        
        blocks = parser.get_processable_blocks()
        markdown = self.converter.convert_blocks(blocks)
        
        self.log(f"Generated {len(markdown)} characters of Markdown", "SUCCESS")
        return markdown
    
    def save_markdown(
        self,
        content: str,
        filename: str,
        output_dir: str
    ) -> Path:
        """
        Save Markdown to file.
        
        Args:
            content: Markdown content
            filename: Output filename
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        self.log(f"Saving to {output_dir}/{filename}", "STEP")
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path = output_path / filename
        file_path.write_text(content, encoding='utf-8')
        
        self.log(f"Saved: {file_path}", "SUCCESS")
        return file_path
    
    # ✅ NEW: Enhanced git_commit_and_push
    def git_commit_and_push(self, repo_path: str, message: str):
        """
        Commit and push changes to Git repository.
        
        Args:
            repo_path: Path to Git repository
            message: Commit message
        """
        self.log("Git operations starting...", "STEP")
        
        try:
            # Change to repo directory
            original_dir = os.getcwd()
            os.chdir(repo_path)
            
            # Check if there are changes to commit
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not status_result.stdout.strip():
                self.log("No changes to commit", "INFO")
                os.chdir(original_dir)
                return
            
            # Git add all changes
            self.log("Adding files to git...", "STEP")
            subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
            self.log("Files staged", "SUCCESS")
            
            # Git commit
            self.log(f"Committing: {message}", "STEP")
            subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
            self.log("Changes committed", "SUCCESS")
            
            # Git push
            self.log("Pushing to remote...", "STEP")
            subprocess.run(['git', 'push'], check=True, capture_output=True)
            self.log("Changes pushed to GitHub", "SUCCESS")
            self.log("🚀 GitHub Pages will rebuild automatically", "SUCCESS")
            
        except subprocess.CalledProcessError as e:
            self.log(f"Git operation failed: {e}", "ERROR")
            if e.stderr:
                error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
                self.log(f"Details: {error_msg}", "ERROR")
            raise
        
        finally:
            # Return to original directory
            os.chdir(original_dir)
    
    async def download_image(self, url: str, output_dir: str) -> str:
        """
        Download image from Notion URL and save locally.
        
        Args:
            url: Notion image URL (will expire)
            output_dir: Directory to save images (content/posts/)
            
        Returns:
            Relative path to saved image for Markdown
            
        Example:
            url = "https://prod-files-secure.s3.us-west-2.amazonaws.com/..."
            → saves to: ../../static/images/f68cb829.png
            → returns: "../../static/images/f68cb829.png" (relative to post)
        """
        self.log(f"Downloading image: {url[:60]}...", "STEP")
        
        try:
            # Extract filename from URL
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            
            # Get the UUID part (second to last in path)
            image_id = path_parts[-2] if len(path_parts) >= 2 else None
            original_filename = path_parts[-1] if path_parts else "image.png"
            
            # Generate a unique filename using first 8 chars of UUID
            if image_id:
                filename = f"{image_id[:8]}_{original_filename}"
            else:
                # Fallback: hash the URL
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                filename = f"{url_hash}_{original_filename}"
            
            # ✅ FIX: Create images directory relative to output_dir
            # output_dir = ../hriteshMaikap.github.io/content/posts
            # images_dir = ../hriteshMaikap.github.io/static/images
            images_dir = Path(output_dir).parent.parent / "static" / "images"
            images_dir.mkdir(parents=True, exist_ok=True)
            
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Save image
                image_path = images_dir / filename
                image_path.write_bytes(response.content)
            
            # ✅ FIX: Return relative path from post location
            # Post is at: content/posts/2025-11-15-post.md
            # Image is at: static/images/image.png
            # Relative path: ../../static/images/image.png
            relative_path = f"../../static/images/{filename}"
            
            self.log(f"Saved image: {filename}", "SUCCESS")
            return relative_path
            
        except Exception as e:
            self.log(f"Failed to download image: {e}", "ERROR")
            # Return original URL as fallback
            return url
    
    async def process_images(self, parser: BlockParser, output_dir: str) -> dict:
        """
        Download all images from Notion and return URL mapping.
        
        Args:
            parser: BlockParser with image blocks
            output_dir: Output directory for markdown
            
        Returns:
            Dict mapping old URLs to new local paths
            
        Example:
            {
                "https://notion.s3.../image.png?...": "/images/f68cb829_image.png",
                ...
            }
        """
        self.log("Processing images...", "STEP")
        
        image_blocks = parser.get_blocks_by_type("image")
        url_mapping = {}
        
        for block in image_blocks:
            content = parser.get_block_content(block)
            if not content:
                continue
            
            # Get image URL
            url = None
            if content.type == "file" and content.file:
                url = content.file.url
            elif content.type == "external" and content.external:
                url = content.external.url
            
            if url:
                # Download and get local path
                local_path = await self.download_image(url, output_dir)
                url_mapping[url] = local_path
        
        self.log(f"Downloaded {len(url_mapping)} images", "SUCCESS")
        return url_mapping
    
    def replace_image_urls(self, markdown: str, url_mapping: dict) -> str:
        """
        Replace Notion image URLs with local paths.
        
        Args:
            markdown: Markdown content with Notion URLs
            url_mapping: Dict of old URL → new local path
            
        Returns:
            Updated markdown with local image paths
        """
        self.log("Replacing image URLs...", "STEP")
        
        updated_markdown = markdown
        
        for old_url, new_path in url_mapping.items():
            # Replace in markdown image syntax: ![caption](old_url)
            updated_markdown = updated_markdown.replace(old_url, new_path)
        
        self.log(f"Replaced {len(url_mapping)} image URLs", "SUCCESS")
        return updated_markdown
    
    def update_posts_index(self, output_dir: str, title: str, filename: str, page_id: str):
        """
        Update posts-index.json with new post metadata.
        
        Args:
            output_dir: Output directory (content/posts/)
            title: Post title
            filename: Generated filename
            page_id: Notion page ID
        """
        self.log("Updating posts index...", "STEP")
        
        # Path to posts-index.json in repo root
        repo_root = Path(output_dir).parent.parent
        index_file = repo_root / "posts-index.json"
        
        # Load existing index or create new
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"posts": []}
        
        # Extract date from filename (YYYY-MM-DD-title.md)
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
        
        # Create post entry
        post_entry = {
            "title": title,
            "date": date_str,
            "url": f"content/posts/{filename.replace('.md', '.html')}",
            "excerpt": f"A post about {title}",  # TODO: Extract from content
            "notion_page_id": page_id
        }
        
        # Check if post already exists (update it)
        existing_index = next(
            (i for i, p in enumerate(data["posts"]) if p.get("notion_page_id") == page_id),
            None
        )
        
        if existing_index is not None:
            data["posts"][existing_index] = post_entry
            self.log(f"Updated existing post in index", "SUCCESS")
        else:
            data["posts"].append(post_entry)
            self.log(f"Added new post to index", "SUCCESS")
        
        # Sort by date (newest first)
        data["posts"].sort(key=lambda x: x["date"], reverse=True)
        
        # Save index
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.log(f"Posts index saved: {index_file}", "SUCCESS")
    
    async def deploy(
        self,
        page_id: str,
        output_dir: str,
        download_images: bool = True,
        auto_commit: bool = False
    ) -> Path:
        """
        Full deployment pipeline.
        
        Args:
            page_id: Notion page ID
            output_dir: Output directory
            download_images: Download images locally
            auto_commit: Auto-commit and push
            
        Returns:
            Path to deployed file
        """
        self.log("=" * 60, "INFO")
        self.log("STARTING DEPLOYMENT", "INFO")
        self.log("=" * 60, "INFO")
        
        async with NotionClient(
            api_token=settings.NOTION_API_TOKEN,
            api_version=settings.API_VERSION
        ) as client:
            self.client = client
            
            # Step 1: Fetch page
            raw_data = await self.fetch_page(page_id)
            
            # Step 2: Parse blocks
            parser = self.parse_blocks(raw_data)
            
            # Step 3: Extract title
            title = self.extract_title(parser)
            
            # Step 4: Generate filename
            filename = self.generate_filename(title)
            
            # Step 5: Convert to Markdown
            markdown = self.convert_to_markdown(parser)
            
            # Step 6: Download images and update URLs
            if download_images:
                url_mapping = await self.process_images(parser, output_dir)
                markdown = self.replace_image_urls(markdown, url_mapping)
            
            # Step 7: Add frontmatter
            frontmatter = self.generate_frontmatter(title, page_id)
            full_content = frontmatter + markdown
            
            # Step 8: Save file
            file_path = self.save_markdown(full_content, filename, output_dir)
            
            # Step 9: Update posts index
            self.update_posts_index(output_dir, title, filename, page_id)
            
            # ✅ Step 10: Git operations (NEW - always run if auto_commit is True)
            if auto_commit:
                repo_path = Path(output_dir).parent.parent
                commit_message = f"deploy: {title}\n\nAuto-deployed from Notion"
                self.git_commit_and_push(str(repo_path), commit_message)
            
            self.log("=" * 60, "INFO")
            self.log("DEPLOYMENT COMPLETE", "SUCCESS")
            self.log("=" * 60, "INFO")
            
            if not auto_commit:
                self.log("⚠️  Changes not committed. Use --auto-commit to push automatically", "WARNING")
            
            return file_path


# ============================================
# CLI COMMANDS (MODIFIED)
# ============================================

@click.group()
def cli():
    """Notion to GitHub Pages deployment tool."""
    pass


# ✅ MODIFIED: Deploy command now supports --page flag
@cli.command()
@click.option(
    '--page',
    help='Page name from deploy-config.json (e.g., clt)'
)
@click.option(
    '--page-id',
    help='Notion page ID (overrides --page)'
)
@click.option(
    '--output-dir',
    help='Output directory (overrides config)'
)
@click.option(
    '--download-images/--no-download-images',
    default=None,
    help='Download images locally (overrides config)'
)
@click.option(
    '--auto-commit/--no-auto-commit',
    default=None,
    help='Auto-commit and push (overrides config)'
)
@click.option(
    '--verbose/--no-verbose',
    default=None,
    help='Verbose output (overrides config)'
)
def deploy(
    page: Optional[str],
    page_id: Optional[str],
    output_dir: Optional[str],
    download_images: Optional[bool],
    auto_commit: Optional[bool],
    verbose: Optional[bool]
):
    """
    Deploy a Notion page to GitHub Pages.
    
    Examples:
    
        # Deploy by page name (from config)
        python main.py deploy --page clt
        
        # Deploy with auto-commit
        python main.py deploy --page clt --auto-commit
        
        # Deploy by page ID
        python main.py deploy --page-id abc123 --verbose
    """
    # Load config
    config = ConfigManager()
    
    # ✅ Determine page ID (--page or --page-id)
    if page_id:
        final_page_id = page_id
        click.echo(f"📄 Using page ID: {page_id}")
    elif page:
        final_page_id = config.get_page_id(page)
        if not final_page_id:
            click.echo(f"❌ Page '{page}' not found in deploy-config.json")
            click.echo("\nAvailable pages:")
            for name, pid in config.list_pages().items():
                click.echo(f"  - {name}: {pid}")
            raise click.Abort()
        click.echo(f"📄 Deploying page: {page} ({final_page_id})")
    else:
        click.echo("❌ Either --page or --page-id is required")
        raise click.Abort()
    
    # ✅ Get settings (CLI overrides config)
    final_output_dir = output_dir or config.get_setting("output_dir", "../hriteshMaikap.github.io/content/posts")
    final_download_images = download_images if download_images is not None else config.get_setting("download_images", True)
    final_auto_commit = auto_commit if auto_commit is not None else config.get_setting("auto_commit", False)
    final_verbose = verbose if verbose is not None else config.get_setting("verbose", False)
    
    async def run_deployment():
        """Async wrapper for deployment."""
        try:
            deployer = Deployer(verbose=final_verbose)
            
            file_path = await deployer.deploy(
                page_id=final_page_id,
                output_dir=final_output_dir,
                download_images=final_download_images,
                auto_commit=final_auto_commit
            )
            
            click.echo(f"\n✅ Deployed to: {file_path}")
            
        except Exception as e:
            click.echo(f"\n❌ Deployment failed: {e}", err=True)
            if final_verbose:
                import traceback
                traceback.print_exc()
            raise click.Abort()
    
    asyncio.run(run_deployment())


# ✅ NEW: List configured pages
@cli.command(name='list-pages')
def list_pages():
    """List all configured pages from deploy-config.json."""
    config = ConfigManager()
    pages = config.list_pages()
    
    if not pages:
        click.echo("No pages configured yet.")
        click.echo("\nAdd pages to deploy-config.json:")
        click.echo('  "pages": { "clt": "page-id-here" }')
        return
    
    click.echo("\n📚 Configured Pages:")
    click.echo("=" * 60)
    for name, page_id in pages.items():
        click.echo(f"  {name:20} → {page_id}")
    click.echo("=" * 60)
    click.echo(f"\nTotal: {len(pages)} page(s)")
    click.echo(f"\nDeploy with: python main.py deploy --page <name>")


# ✅ NEW: Remove deployed page
@cli.command(name='remove')
@click.option(
    '--page',
    help='Page name from deploy-config.json (e.g., clt)'
)
@click.option(
    '--page-id',
    help='Notion page ID (overrides --page)'
)
@click.option(
    '--auto-commit/--no-auto-commit',
    default=None,
    help='Auto-commit and push after removal (overrides config)'
)
@click.option(
    '--verbose/--no-verbose',
    default=None,
    help='Verbose output (overrides config)'
)
def remove(
    page: Optional[str],
    page_id: Optional[str],
    auto_commit: Optional[bool],
    verbose: Optional[bool]
):
    """
    Remove a deployed page from GitHub Pages.
    
    This will:
    1. Find the markdown file by page ID
    2. Delete the markdown file
    3. Remove from posts-index.json
    4. Delete associated images (if no other posts use them)
    5. Optionally commit and push changes
    
    Examples:
    
        # Remove by page name
        python main.py remove --page clt
        
        # Remove with auto-commit
        python main.py remove --page clt --auto-commit
        
        # Remove by page ID
        python main.py remove --page-id abc123 --verbose
    """
    # Load config
    config = ConfigManager()
    
    # Determine page ID
    if page_id:
        final_page_id = page_id
        click.echo(f"📄 Removing page ID: {page_id}")
    elif page:
        final_page_id = config.get_page_id(page)
        if not final_page_id:
            click.echo(f"❌ Page '{page}' not found in deploy-config.json")
            click.echo("\nAvailable pages:")
            for name, pid in config.list_pages().items():
                click.echo(f"  - {name}: {pid}")
            raise click.Abort()
        click.echo(f"📄 Removing page: {page} ({final_page_id})")
    else:
        click.echo("❌ Either --page or --page-id is required")
        raise click.Abort()
    
    # Get settings
    output_dir = config.get_setting("output_dir", "../hriteshMaikap.github.io/content/posts")
    final_auto_commit = auto_commit if auto_commit is not None else config.get_setting("auto_commit", False)
    final_verbose = verbose if verbose is not None else config.get_setting("verbose", False)
    
    def log(message: str, level: str = "INFO"):
        """Log message if verbose."""
        if final_verbose:
            icon = {
                "INFO": "ℹ️",
                "SUCCESS": "✅",
                "ERROR": "❌",
                "WARNING": "⚠️",
                "STEP": "🔹"
            }.get(level, "ℹ️")
            click.echo(f"{icon} {message}")
    
    try:
        log("=" * 60, "INFO")
        log("STARTING REMOVAL", "INFO")
        log("=" * 60, "INFO")
        
        repo_root = Path(output_dir).parent.parent
        posts_dir = Path(output_dir)
        index_file = repo_root / "posts-index.json"
        
        # Step 1: Find post in index
        log("Searching posts index...", "STEP")
        
        if not index_file.exists():
            click.echo("❌ posts-index.json not found")
            raise click.Abort()
        
        with open(index_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find post by page_id
        post_index = next(
            (i for i, p in enumerate(data["posts"]) if p.get("notion_page_id") == final_page_id),
            None
        )
        
        if post_index is None:
            click.echo(f"❌ No deployed post found with page_id: {final_page_id}")
            click.echo("\nDeployed posts:")
            for p in data["posts"]:
                click.echo(f"  - {p['title']} ({p.get('notion_page_id', 'no ID')})")
            raise click.Abort()
        
        post_data = data["posts"][post_index]
        title = post_data["title"]
        
        log(f"Found post: {title}", "SUCCESS")
        
        # Step 2: Find and delete markdown file
        log("Finding markdown file...", "STEP")
        
        # Search for file with matching page_id in frontmatter
        md_file = None
        for file in posts_dir.glob("*.md"):
            content = file.read_text(encoding='utf-8')
            if f'notion_page_id: "{final_page_id}"' in content:
                md_file = file
                break
        
        if md_file:
            log(f"Deleting: {md_file.name}", "STEP")
            
            # Extract image URLs before deleting
            content = md_file.read_text(encoding='utf-8')
            image_pattern = r'!\[.*?\]\((.*?)\)'
            images_in_post = re.findall(image_pattern, content)
            
            # Delete markdown file
            md_file.unlink()
            log(f"Deleted: {md_file.name}", "SUCCESS")
        else:
            log(f"Markdown file not found (will still remove from index)", "WARNING")
            images_in_post = []
        
        # Step 3: Remove from posts index
        log("Updating posts index...", "STEP")
        
        data["posts"].pop(post_index)
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log(f"Removed from posts index", "SUCCESS")
        
        # Step 4: Delete associated images (optional - only if not used elsewhere)
        if images_in_post:
            log("Checking for unused images...", "STEP")
            
            # Get all remaining markdown files
            all_md_files = list(posts_dir.glob("*.md"))
            
            # Check which images are still in use
            images_to_delete = []
            for img_path in images_in_post:
                if img_path.startswith("../../static/images/"):
                    # Check if this image is used in any other post
                    img_name = img_path.split("/")[-1]
                    
                    still_in_use = False
                    for other_file in all_md_files:
                        if other_file != md_file:
                            other_content = other_file.read_text(encoding='utf-8')
                            if img_name in other_content:
                                still_in_use = True
                                break
                    
                    if not still_in_use:
                        images_to_delete.append(img_path)
            
            # Delete unused images
            if images_to_delete:
                images_dir = repo_root / "static" / "images"
                for img_path in images_to_delete:
                    img_name = img_path.split("/")[-1]
                    img_file = images_dir / img_name
                    
                    if img_file.exists():
                        img_file.unlink()
                        log(f"Deleted image: {img_name}", "SUCCESS")
                
                log(f"Deleted {len(images_to_delete)} unused image(s)", "SUCCESS")
            else:
                log("No unused images to delete", "INFO")
        
        # Step 5: Git commit and push
        if final_auto_commit:
            log("Git operations starting...", "STEP")
            
            original_dir = os.getcwd()
            os.chdir(str(repo_root))
            
            # Check for changes
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                check=True
            )
            
            if status_result.stdout.strip():
                # Git add
                log("Adding files to git...", "STEP")
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                log("Files staged", "SUCCESS")
                
                # Git commit
                commit_message = f"remove: {title}\n\nRemoved from Notion deployment"
                log(f"Committing: {commit_message}", "STEP")
                subprocess.run(['git', 'commit', '-m', commit_message], check=True, capture_output=True)
                log("Changes committed", "SUCCESS")
                
                # Git push
                log("Pushing to remote...", "STEP")
                subprocess.run(['git', 'push'], check=True, capture_output=True)
                log("Changes pushed to GitHub", "SUCCESS")
                log("🚀 GitHub Pages will rebuild automatically", "SUCCESS")
            else:
                log("No changes to commit", "INFO")
            
            os.chdir(original_dir)
        
        log("=" * 60, "INFO")
        log("REMOVAL COMPLETE", "SUCCESS")
        log("=" * 60, "INFO")
        
        if not final_auto_commit:
            log("⚠️  Changes not committed. Use --auto-commit to push automatically", "WARNING")
        
        click.echo(f"\n✅ Successfully removed: {title}")
        
    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ Git operation failed: {e}", err=True)
        if e.stderr:
            error_msg = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
            click.echo(f"Details: {error_msg}", err=True)
        raise click.Abort()
    
    except Exception as e:
        click.echo(f"\n❌ Removal failed: {e}", err=True)
        if final_verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()
    
if __name__ == '__main__':
    cli()