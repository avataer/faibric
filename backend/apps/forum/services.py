"""
Forum service for managing community discussions.
"""
import logging
from typing import List, Dict, Optional
from django.utils import timezone
from django.db import transaction
import markdown

from .models import (
    ForumConfig, Category, Board, Thread, Post,
    PostReaction, Report, UserBan
)

logger = logging.getLogger(__name__)


class ForumService:
    """
    Service for forum operations.
    """
    
    def __init__(self, tenant: 'Tenant'):
        self.tenant = tenant
        self._config = None
    
    @property
    def config(self) -> ForumConfig:
        if self._config is None:
            self._config, _ = ForumConfig.objects.get_or_create(
                tenant=self.tenant
            )
        return self._config
    
    def is_user_banned(self, user_id: str) -> bool:
        """Check if user is banned."""
        ban = UserBan.objects.filter(
            tenant=self.tenant,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not ban:
            return False
        
        if ban.is_expired:
            ban.is_active = False
            ban.save(update_fields=['is_active'])
            return False
        
        return True
    
    # ============= BOARDS =============
    
    def get_boards(self, include_private: bool = False) -> List[Board]:
        """Get all boards."""
        qs = Board.objects.filter(
            tenant=self.tenant,
            is_active=True
        ).select_related('category')
        
        if not include_private:
            qs = qs.filter(is_private=False)
        
        return list(qs)
    
    def get_board(self, board_id: str) -> Optional[Board]:
        """Get a board by ID."""
        try:
            return Board.objects.get(
                id=board_id,
                tenant=self.tenant,
                is_active=True
            )
        except Board.DoesNotExist:
            return None
    
    # ============= THREADS =============
    
    def get_threads(
        self,
        board: Board,
        page: int = 1,
        per_page: int = 20
    ) -> List[Thread]:
        """Get threads in a board."""
        offset = (page - 1) * per_page
        
        return list(
            Thread.objects.filter(
                board=board,
                is_deleted=False,
                is_approved=True
            ).order_by('-is_pinned', '-last_post_at')[offset:offset + per_page]
        )
    
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        try:
            thread = Thread.objects.select_related('board').get(
                id=thread_id,
                is_deleted=False
            )
            
            # Increment view count
            thread.view_count += 1
            thread.save(update_fields=['view_count'])
            
            return thread
        except Thread.DoesNotExist:
            return None
    
    @transaction.atomic
    def create_thread(
        self,
        board: Board,
        title: str,
        content: str,
        author_id: str,
        author_name: str,
        author_avatar: str = ''
    ) -> Thread:
        """Create a new thread."""
        if self.is_user_banned(author_id):
            raise ValueError("User is banned from posting")
        
        # Create thread
        thread = Thread.objects.create(
            board=board,
            title=title,
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            content_preview=content[:200],
            is_approved=not self.config.require_approval_for_posts,
            last_post_by=author_name
        )
        
        # Create first post
        Post.objects.create(
            thread=thread,
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            content=content,
            content_html=self._render_content(content),
            is_first_post=True,
            is_approved=thread.is_approved
        )
        
        # Update board stats
        board.update_stats()
        
        return thread
    
    def update_thread(
        self,
        thread: Thread,
        title: str = None,
        is_pinned: bool = None,
        is_locked: bool = None,
        is_featured: bool = None
    ) -> Thread:
        """Update thread properties."""
        if title is not None:
            thread.title = title
        if is_pinned is not None:
            thread.is_pinned = is_pinned
        if is_locked is not None:
            thread.is_locked = is_locked
        if is_featured is not None:
            thread.is_featured = is_featured
        
        thread.save()
        return thread
    
    def delete_thread(
        self,
        thread: Thread,
        deleted_by: str,
        reason: str = ''
    ) -> Thread:
        """Soft delete a thread."""
        thread.is_deleted = True
        thread.deleted_at = timezone.now()
        thread.deleted_by = deleted_by
        thread.delete_reason = reason
        thread.save()
        
        thread.board.update_stats()
        
        return thread
    
    # ============= POSTS =============
    
    def get_posts(self, thread: Thread) -> List[Post]:
        """Get posts in a thread."""
        return list(
            Post.objects.filter(
                thread=thread,
                is_deleted=False,
                is_approved=True
            ).order_by('created_at')
        )
    
    @transaction.atomic
    def create_post(
        self,
        thread: Thread,
        content: str,
        author_id: str,
        author_name: str,
        author_avatar: str = '',
        parent_id: str = None
    ) -> Post:
        """Create a reply in a thread."""
        if self.is_user_banned(author_id):
            raise ValueError("User is banned from posting")
        
        if thread.is_locked:
            raise ValueError("Thread is locked")
        
        parent = None
        if parent_id:
            try:
                parent = Post.objects.get(id=parent_id, thread=thread)
            except Post.DoesNotExist:
                pass
        
        post = Post.objects.create(
            thread=thread,
            parent=parent,
            author_id=author_id,
            author_name=author_name,
            author_avatar=author_avatar,
            content=content,
            content_html=self._render_content(content),
            is_approved=not self.config.require_approval_for_posts
        )
        
        # Update thread stats
        thread.update_stats()
        thread.board.update_stats()
        
        return post
    
    def update_post(
        self,
        post: Post,
        content: str,
        editor_id: str
    ) -> Post:
        """Edit a post."""
        if post.author_id != editor_id:
            raise ValueError("Only the author can edit this post")
        
        post.content = content
        post.content_html = self._render_content(content)
        post.is_edited = True
        post.edited_at = timezone.now()
        post.edit_count += 1
        post.save()
        
        return post
    
    def delete_post(
        self,
        post: Post,
        deleted_by: str,
        reason: str = ''
    ) -> Post:
        """Soft delete a post."""
        post.is_deleted = True
        post.deleted_at = timezone.now()
        post.deleted_by = deleted_by
        post.delete_reason = reason
        post.save()
        
        post.thread.update_stats()
        post.thread.board.update_stats()
        
        return post
    
    # ============= REACTIONS =============
    
    def react_to_post(
        self,
        post: Post,
        user_id: str,
        reaction_type: str
    ) -> Post:
        """Add or change reaction to a post."""
        existing = PostReaction.objects.filter(
            post=post,
            user_id=user_id
        ).first()
        
        if existing:
            if existing.reaction_type == reaction_type:
                # Remove reaction
                if reaction_type == 'upvote':
                    post.upvotes = max(0, post.upvotes - 1)
                else:
                    post.downvotes = max(0, post.downvotes - 1)
                existing.delete()
            else:
                # Change reaction
                if reaction_type == 'upvote':
                    post.upvotes += 1
                    post.downvotes = max(0, post.downvotes - 1)
                else:
                    post.downvotes += 1
                    post.upvotes = max(0, post.upvotes - 1)
                existing.reaction_type = reaction_type
                existing.save()
        else:
            # New reaction
            PostReaction.objects.create(
                post=post,
                user_id=user_id,
                reaction_type=reaction_type
            )
            if reaction_type == 'upvote':
                post.upvotes += 1
            else:
                post.downvotes += 1
        
        post.save(update_fields=['upvotes', 'downvotes'])
        return post
    
    # ============= REPORTS =============
    
    def create_report(
        self,
        reporter_id: str,
        reporter_name: str,
        reason: str,
        description: str = '',
        thread: Thread = None,
        post: Post = None
    ) -> Report:
        """Create a report."""
        report = Report.objects.create(
            tenant=self.tenant,
            thread=thread,
            post=post,
            reporter_id=reporter_id,
            reporter_name=reporter_name,
            reason=reason,
            description=description
        )
        
        # Increment report count on post
        if post:
            post.report_count += 1
            if post.report_count >= 5:  # Auto-hide after 5 reports
                post.is_hidden = True
            post.save(update_fields=['report_count', 'is_hidden'])
        
        return report
    
    def resolve_report(
        self,
        report: Report,
        resolved_by: str,
        status: str,
        notes: str = ''
    ) -> Report:
        """Resolve a report."""
        report.status = status
        report.resolved_by = resolved_by
        report.resolved_at = timezone.now()
        report.resolution_notes = notes
        report.save()
        
        return report
    
    # ============= BANS =============
    
    def ban_user(
        self,
        user_id: str,
        user_name: str,
        reason: str,
        banned_by: str,
        is_permanent: bool = False,
        expires_at: str = None
    ) -> UserBan:
        """Ban a user."""
        ban, created = UserBan.objects.update_or_create(
            tenant=self.tenant,
            user_id=user_id,
            defaults={
                'user_name': user_name,
                'reason': reason,
                'banned_by': banned_by,
                'is_permanent': is_permanent,
                'expires_at': expires_at,
                'is_active': True
            }
        )
        return ban
    
    def unban_user(self, user_id: str) -> bool:
        """Unban a user."""
        count = UserBan.objects.filter(
            tenant=self.tenant,
            user_id=user_id
        ).update(is_active=False)
        return count > 0
    
    # ============= HELPERS =============
    
    def _render_content(self, content: str) -> str:
        """Render markdown content to HTML."""
        try:
            return markdown.markdown(
                content,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
        except Exception:
            return content









