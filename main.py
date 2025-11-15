"""
Deploy Notion pages to Hugo static site.

This CLI tool fetches Notion pages, converts them to Markdown,
and deploys them to your Hugo site with proper frontmatter.

Usage:
    python main.py deploy --page-id <notion-page-id>
    
    python main.py deploy \
        --page-id abc123 \
        --output-dir ../hriteshMaikap.github.io/content/posts \
        --download-images \
        --auto-commit
        
    python main.py deploy --page-id abc123 --verbose
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
    
    def git_commit_and_push(self, repo_path: str, message: str):
        """
        Commit and push changes to Git repository.
        
        Args:
            repo_path: Path to Git repository
            message: Commit message
        """
        self.log("Committing changes...", "STEP")
        
        try:
            # Change to repo directory
            original_dir = os.getcwd()
            os.chdir(repo_path)
            
            # Git add
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Git commit
            subprocess.run(['git', 'commit', '-m', message], check=True)
            
            # Git push
            subprocess.run(['git', 'push'], check=True)
            
            self.log("Changes pushed to GitHub", "SUCCESS")
            
        except subprocess.CalledProcessError as e:
            self.log(f"Git operation failed: {e}", "ERROR")
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
            
            # Step 6: Download images and update URLs ✅ NEW
            if download_images:
                url_mapping = await self.process_images(parser, output_dir)
                markdown = self.replace_image_urls(markdown, url_mapping)
            
            # Step 7: Add frontmatter
            frontmatter = self.generate_frontmatter(title, page_id)
            full_content = frontmatter + markdown
            
            # Step 8: Save file
            file_path = self.save_markdown(full_content, filename, output_dir)
            
            # Step 9: Git operations
            if auto_commit:
                repo_path = Path(output_dir).parent.parent
                commit_message = f"Add: {title}"
                self.git_commit_and_push(str(repo_path), commit_message)
            
            self.log("=" * 60, "INFO")
            self.log("DEPLOYMENT COMPLETE", "SUCCESS")
            self.log("=" * 60, "INFO")
            
            return file_path


# ============================================
# CLI COMMANDS
# ============================================

@click.group()
def cli():
    """Notion to GitHub Pages deployment tool."""
    pass


@cli.command()
@click.option(
    '--page-id',
    required=True,
    help='Notion page ID to deploy'
)
@click.option(
    '--output-dir',
    default='../hriteshMaikap.github.io/content/posts',
    help='Output directory for Markdown file'
)
@click.option(
    '--download-images/--no-download-images',
    default=True,
    help='Download and save images locally'
)
@click.option(
    '--auto-commit/--no-auto-commit',
    default=False,
    help='Automatically commit and push changes'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Verbose output'
)
def deploy(
    page_id: str,
    output_dir: str,
    download_images: bool,
    auto_commit: bool,
    verbose: bool
):
    """
    Deploy a Notion page to Hugo site.
    
    Example:
        python main.py deploy --page-id abc123 --verbose
        
        python main.py deploy --page-id abc123 --auto-commit
    """
    async def run_deployment():
        """Async wrapper for deployment."""
        try:
            # Create deployer (settings loaded automatically)
            deployer = Deployer(verbose=verbose)
            
            # Deploy (async)
            file_path = await deployer.deploy(
                page_id=page_id,
                output_dir=output_dir,
                download_images=download_images,
                auto_commit=auto_commit
            )
            
            click.echo(f"\n✅ Deployed to: {file_path}")
            
        except Exception as e:
            click.echo(f"\n❌ Deployment failed: {e}", err=True)
            if verbose:
                import traceback
                traceback.print_exc()
            raise click.Abort()
    
    # ✅ Run async function
    asyncio.run(run_deployment())


if __name__ == '__main__':
    cli()