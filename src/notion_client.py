"""Notion API client wrapper."""

import os
from typing import Optional, List, Dict, Any
from notion_client import Client
from dotenv import load_dotenv
from rich.console import Console

from .models import NotionContent

load_dotenv()

console = Console()


class NotionClientWrapper:
    """Wrapper for Notion API interactions."""
    
    def __init__(self):
        """Initialize the Notion client with API key from environment."""
        self.api_key = os.getenv("NOTION_API_KEY")
        self.page_id = os.getenv("NOTION_PAGE_ID")
        self.database_id = os.getenv("NOTION_DATABASE_ID")
        
        if not self.api_key:
            raise ValueError("NOTION_API_KEY not found in environment variables")
        
        self.client = Client(auth=self.api_key)
    
    def get_content(self) -> Optional[NotionContent]:
        """
        Fetch content from the Notion page.
        
        Returns:
            NotionContent object or None if error
        """
        try:
            # Fetch the page
            page = self.client.pages.retrieve(page_id=self.page_id)
            return self._parse_page(page)
            
        except Exception as e:
            console.print(f"[red]Error fetching from Notion: {e}[/red]")
            raise
    
    def _parse_page(self, page: Dict[str, Any]) -> NotionContent:
        """Parse a Notion page into NotionContent model."""
        page_id = page["id"]
        
        # Extract title (try different common property names)
        title = ""
        properties = page.get("properties", {})
        
        for title_prop in ["Name", "Title", "title", "name"]:
            if title_prop in properties:
                prop = properties[title_prop]
                if prop["type"] == "title" and prop["title"]:
                    title = "".join([text["plain_text"] for text in prop["title"]])
                    break
        
        # Get the page content (blocks)
        content = self._get_page_content(page_id)
        
        # Extract other properties
        parsed_properties = {}
        for prop_name, prop_data in properties.items():
            prop_type = prop_data["type"]
            if prop_type == "rich_text" and prop_data["rich_text"]:
                parsed_properties[prop_name] = "".join([text["plain_text"] for text in prop_data["rich_text"]])
            elif prop_type == "select" and prop_data["select"]:
                parsed_properties[prop_name] = prop_data["select"]["name"]
            elif prop_type == "status" and prop_data["status"]:
                parsed_properties[prop_name] = prop_data["status"]["name"]
        
        return NotionContent(
            id=page_id,
            title=title,
            content=content,
            properties=parsed_properties
        )
    
    def _get_page_content(self, page_id: str) -> str:
        """Retrieve the text content from a Notion page."""
        try:
            blocks = self.client.blocks.children.list(block_id=page_id)
            content_parts = []
            
            for block in blocks["results"]:
                block_type = block["type"]
                
                # Extract text from different block types
                if block_type == "paragraph":
                    if block["paragraph"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["paragraph"]["rich_text"]])
                        content_parts.append(text)
                
                elif block_type == "heading_1":
                    if block["heading_1"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["heading_1"]["rich_text"]])
                        content_parts.append(f"# {text}")
                
                elif block_type == "heading_2":
                    if block["heading_2"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["heading_2"]["rich_text"]])
                        content_parts.append(f"## {text}")
                
                elif block_type == "heading_3":
                    if block["heading_3"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["heading_3"]["rich_text"]])
                        content_parts.append(f"### {text}")
                
                elif block_type == "bulleted_list_item":
                    if block["bulleted_list_item"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["bulleted_list_item"]["rich_text"]])
                        content_parts.append(f"• {text}")
                
                elif block_type == "numbered_list_item":
                    if block["numbered_list_item"]["rich_text"]:
                        text = "".join([text["plain_text"] for text in block["numbered_list_item"]["rich_text"]])
                        content_parts.append(f"- {text}")
            
            return "\n\n".join(content_parts)
        
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch page content: {e}[/yellow]")
            return ""
    
    def add_comment(self, page_id: str, comment: str) -> bool:
        """
        Add a comment to the Notion page (optional tracking).
        
        Args:
            page_id: The ID of the Notion page
            comment: The comment to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.comments.create(
                parent={"page_id": page_id},
                rich_text=[{
                    "type": "text",
                    "text": {"content": comment}
                }]
            )
            return True
        except Exception as e:
            console.print(f"[yellow]Note: Could not add comment to Notion: {e}[/yellow]")
            return False
    
    def get_database_pages(self) -> List[Dict]:
        """
        Fetch all pages from a Notion database.
        
        Returns:
            List of page dictionaries with id, title, content, last_edited_time
        """
        if not self.database_id:
            # Fallback to single page if database not configured
            if self.page_id:
                page = self.get_content()
                if page:
                    return [{
                        'id': page.id,
                        'title': page.title,
                        'content': page.content,
                        'last_edited_time': None  # Would need to fetch from API
                    }]
            return []
        
        try:
            pages = []
            has_more = True
            start_cursor = None
            
            while has_more:
                if start_cursor:
                    response = self.client.databases.query(
                        database_id=self.database_id,
                        start_cursor=start_cursor
                    )
                else:
                    response = self.client.databases.query(
                        database_id=self.database_id
                    )
                
                for page in response.get("results", []):
                    page_id = page["id"]
                    title = ""
                    
                    # Extract title from properties
                    properties = page.get("properties", {})
                    for title_prop in ["Name", "Title", "title", "name"]:
                        if title_prop in properties:
                            prop = properties[title_prop]
                            if prop["type"] == "title" and prop["title"]:
                                title = "".join([text["plain_text"] for text in prop["title"]])
                                break
                    
                    # Get content
                    content = self._get_page_content(page_id)
                    
                    # Get last edited time
                    last_edited_time = page.get("last_edited_time")
                    
                    pages.append({
                        'id': page_id,
                        'title': title,
                        'content': content,
                        'last_edited_time': last_edited_time,
                        'properties': properties
                    })
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            console.print(f"[green]✓ Fetched {len(pages)} pages from database[/green]")
            return pages
            
        except Exception as e:
            console.print(f"[red]Error fetching database pages: {e}[/red]")
            raise
