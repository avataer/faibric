from rest_framework import serializers
from .models import AnalyticsConfig, Event, Funnel, FunnelStep, FunnelConversion, UserProfile


class AnalyticsConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsConfig
        fields = [
            'id', 'mixpanel_enabled', 'mixpanel_token',
            'ga_enabled', 'ga_measurement_id',
            'webhook_enabled', 'webhook_url',
            'internal_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'mixpanel_token': {'write_only': True},
            'ga_api_secret': {'write_only': True},
            'webhook_secret': {'write_only': True},
        }


class TrackEventSerializer(serializers.Serializer):
    """Serializer for tracking events from customer's apps."""
    event = serializers.CharField(max_length=100)
    distinct_id = serializers.CharField(max_length=200, required=False)
    anonymous_id = serializers.CharField(max_length=200, required=False)
    user_id = serializers.CharField(max_length=200, required=False)
    properties = serializers.DictField(required=False, default=dict)
    context = serializers.DictField(required=False, default=dict)
    timestamp = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        # Must have at least one identifier
        if not any([data.get('distinct_id'), data.get('anonymous_id'), data.get('user_id')]):
            raise serializers.ValidationError(
                "At least one of distinct_id, anonymous_id, or user_id is required"
            )
        return data


class IdentifyUserSerializer(serializers.Serializer):
    """Serializer for identifying users."""
    distinct_id = serializers.CharField(max_length=200, required=False)
    user_id = serializers.CharField(max_length=200, required=False)
    traits = serializers.DictField(required=False, default=dict)
    
    def validate(self, data):
        if not any([data.get('distinct_id'), data.get('user_id')]):
            raise serializers.ValidationError(
                "Either distinct_id or user_id is required"
            )
        return data


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            'id', 'event_name', 'distinct_id', 'user_id',
            'properties', 'context', 'source', 'timestamp'
        ]


class FunnelStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = FunnelStep
        fields = ['id', 'order', 'name', 'event_name', 'property_filters']


class FunnelSerializer(serializers.ModelSerializer):
    steps = FunnelStepSerializer(many=True, read_only=True)
    
    class Meta:
        model = Funnel
        fields = [
            'id', 'name', 'description', 'is_template', 'template_name',
            'is_active', 'conversion_window_hours', 'steps',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FunnelCreateSerializer(serializers.ModelSerializer):
    steps = FunnelStepSerializer(many=True)
    
    class Meta:
        model = Funnel
        fields = ['name', 'description', 'conversion_window_hours', 'steps']
    
    def create(self, validated_data):
        steps_data = validated_data.pop('steps')
        funnel = Funnel.objects.create(**validated_data)
        
        for i, step_data in enumerate(steps_data):
            FunnelStep.objects.create(
                funnel=funnel,
                order=i + 1,
                **step_data
            )
        
        return funnel


class FunnelStatsSerializer(serializers.Serializer):
    funnel_id = serializers.UUIDField()
    funnel_name = serializers.CharField()
    period_days = serializers.IntegerField()
    total_started = serializers.IntegerField()
    total_completed = serializers.IntegerField()
    overall_conversion_rate = serializers.FloatField()
    steps = serializers.ListField()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'id', 'distinct_id', 'properties',
            'first_seen', 'last_seen', 'total_events'
        ]


class FunnelTemplateSerializer(serializers.Serializer):
    """Serializer for funnel templates."""
    template_name = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    steps = serializers.ListField()

