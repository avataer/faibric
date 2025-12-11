"""
Serializers for marketing analysis API.
"""
from rest_framework import serializers

from .models import (
    Competitor,
    CompetitorChange,
    CompetitorSnapshot,
    Keyword,
    KeywordRanking,
    MarketingConfig,
    MarketingReport,
    ReportTemplate,
)


class MarketingConfigSerializer(serializers.ModelSerializer):
    """Serializer for marketing configuration."""
    
    class Meta:
        model = MarketingConfig
        fields = [
            'id',
            'report_frequency',
            'report_email',
            'report_enabled',
            'additional_recipients',
            'last_report_at',
            'next_report_at',
            'settings',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_report_at', 'next_report_at', 'created_at', 'updated_at']


class CompetitorSerializer(serializers.ModelSerializer):
    """Serializer for competitors."""
    
    change_count = serializers.SerializerMethodField()
    snapshot_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Competitor
        fields = [
            'id',
            'name',
            'domain',
            'website_url',
            'track_homepage',
            'track_blog',
            'track_pricing',
            'track_features',
            'custom_pages',
            'is_active',
            'last_scraped_at',
            'notes',
            'change_count',
            'snapshot_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_scraped_at', 'created_at', 'updated_at']
    
    def get_change_count(self, obj):
        return obj.changes.count()
    
    def get_snapshot_count(self, obj):
        return obj.snapshots.count()


class CompetitorCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating competitors."""
    
    class Meta:
        model = Competitor
        fields = [
            'name',
            'domain',
            'website_url',
            'track_homepage',
            'track_blog',
            'track_pricing',
            'track_features',
            'custom_pages',
            'notes',
        ]


class CompetitorSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for competitor snapshots."""
    
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    
    class Meta:
        model = CompetitorSnapshot
        fields = [
            'id',
            'competitor',
            'competitor_name',
            'page_type',
            'page_url',
            'title',
            'meta_description',
            'headings',
            'features_mentioned',
            'pricing_info',
            'blog_posts',
            'http_status',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CompetitorChangeSerializer(serializers.ModelSerializer):
    """Serializer for competitor changes."""
    
    competitor_name = serializers.CharField(source='competitor.name', read_only=True)
    competitor_domain = serializers.CharField(source='competitor.domain', read_only=True)
    
    class Meta:
        model = CompetitorChange
        fields = [
            'id',
            'competitor',
            'competitor_name',
            'competitor_domain',
            'change_type',
            'page_type',
            'page_url',
            'title',
            'description',
            'ai_summary',
            'ai_recommendations',
            'importance_score',
            'is_reviewed',
            'reviewed_by',
            'reviewed_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class KeywordSerializer(serializers.ModelSerializer):
    """Serializer for keywords."""
    
    current_ranking = serializers.SerializerMethodField()
    ranking_trend = serializers.SerializerMethodField()
    
    class Meta:
        model = Keyword
        fields = [
            'id',
            'keyword',
            'your_domain',
            'track_competitors',
            'is_active',
            'last_checked_at',
            'notes',
            'current_ranking',
            'ranking_trend',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'last_checked_at', 'created_at', 'updated_at']
    
    def get_current_ranking(self, obj):
        latest = obj.rankings.filter(domain=obj.your_domain).order_by('-created_at').first()
        return latest.position if latest else None
    
    def get_ranking_trend(self, obj):
        latest = obj.rankings.filter(domain=obj.your_domain).order_by('-created_at').first()
        return latest.position_change if latest else 0


class KeywordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating keywords."""
    
    class Meta:
        model = Keyword
        fields = [
            'keyword',
            'your_domain',
            'track_competitors',
            'notes',
        ]


class KeywordRankingSerializer(serializers.ModelSerializer):
    """Serializer for keyword rankings."""
    
    keyword_text = serializers.CharField(source='keyword.keyword', read_only=True)
    
    class Meta:
        model = KeywordRanking
        fields = [
            'id',
            'keyword',
            'keyword_text',
            'domain',
            'position',
            'title',
            'url',
            'snippet',
            'search_engine',
            'search_location',
            'previous_position',
            'position_change',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MarketingReportSerializer(serializers.ModelSerializer):
    """Serializer for marketing reports."""
    
    class Meta:
        model = MarketingReport
        fields = [
            'id',
            'report_type',
            'period_start',
            'period_end',
            'title',
            'summary',
            'ai_executive_summary',
            'ai_key_insights',
            'ai_action_items',
            'status',
            'sent_to',
            'sent_at',
            'open_count',
            'click_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MarketingReportDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for marketing reports including all data."""
    
    class Meta:
        model = MarketingReport
        fields = [
            'id',
            'report_type',
            'period_start',
            'period_end',
            'title',
            'summary',
            'competitor_analysis',
            'keyword_rankings',
            'changes_detected',
            'recommendations',
            'ai_executive_summary',
            'ai_key_insights',
            'ai_action_items',
            'html_content',
            'status',
            'sent_to',
            'sent_at',
            'error_message',
            'open_count',
            'click_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for report templates."""
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id',
            'name',
            'description',
            'include_competitor_analysis',
            'include_keyword_rankings',
            'include_changes',
            'include_recommendations',
            'include_ai_insights',
            'html_template',
            'primary_color',
            'logo_url',
            'is_default',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardSerializer(serializers.Serializer):
    """Serializer for marketing dashboard data."""
    
    competitors_tracked = serializers.IntegerField()
    keywords_tracked = serializers.IntegerField()
    changes_last_7_days = serializers.IntegerField()
    reports_generated = serializers.IntegerField()
    
    top_changes = CompetitorChangeSerializer(many=True)
    keyword_summary = serializers.ListField()
    recent_reports = MarketingReportSerializer(many=True)
    insights = serializers.ListField()


class GenerateReportRequestSerializer(serializers.Serializer):
    """Serializer for generate report request."""
    
    period_start = serializers.DateField(required=False)
    period_end = serializers.DateField(required=False)
    send_email = serializers.BooleanField(default=True)


class ScrapeCompetitorRequestSerializer(serializers.Serializer):
    """Serializer for scrape competitor request."""
    
    competitor_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of competitor IDs to scrape. If empty, scrapes all."
    )


class CheckKeywordsRequestSerializer(serializers.Serializer):
    """Serializer for check keywords request."""
    
    keyword_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of keyword IDs to check. If empty, checks all."
    )







