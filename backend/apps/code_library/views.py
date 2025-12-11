"""
API views for code library.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Q

from apps.tenants.models import Tenant, TenantMembership

from .models import (
    LibraryCategory,
    LibraryItem,
    LibraryVersion,
    Constraint,
)
from .serializers import (
    LibraryCategorySerializer,
    LibraryItemSerializer,
    LibraryItemCreateSerializer,
    LibraryItemDetailSerializer,
    LibraryVersionSerializer,
    ConstraintSerializer,
    LibrarySearchSerializer,
    LibrarySearchResultSerializer,
    GenerateCodeRequestSerializer,
    GenerateCodeResponseSerializer,
    ResearchRequestSerializer,
)
from .search import LibrarySearchService
from .embeddings import embed_code_sync

from apps.ai_engine.v6.pipeline import CodeGenerationPipeline, GenerationRequest
from apps.ai_engine.v6.research import research_topic_sync
from apps.ai_engine.v6.constraints import ConstraintLoader


class TenantMixin:
    """Mixin to filter querysets by tenant."""
    
    def get_tenant(self):
        tenant_id = self.request.headers.get('X-Tenant-ID')
        if tenant_id:
            return Tenant.objects.filter(id=tenant_id).first()
        
        membership = TenantMembership.objects.filter(
            user=self.request.user,
            is_active=True
        ).first()
        return membership.tenant if membership else None


class LibraryCategoryViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for library categories.
    """
    serializer_class = LibraryCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LibraryCategory.objects.all().order_by('name')


class LibraryItemViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for library items.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return LibraryItemCreateSerializer
        elif self.action == 'retrieve':
            return LibraryItemDetailSerializer
        return LibraryItemSerializer
    
    def get_queryset(self):
        tenant = self.get_tenant()
        
        qs = LibraryItem.objects.filter(is_active=True)
        
        if tenant:
            qs = qs.filter(
                Q(tenant=tenant) | Q(is_public=True) | Q(tenant__isnull=True)
            )
        else:
            qs = qs.filter(Q(is_public=True) | Q(tenant__isnull=True))
        
        # Apply filters
        item_type = self.request.query_params.get('type')
        if item_type:
            qs = qs.filter(item_type=item_type)
        
        language = self.request.query_params.get('language')
        if language:
            qs = qs.filter(language=language)
        
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category_id=category)
        
        return qs.order_by('-quality_score', '-usage_count')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        
        # Generate embedding
        code = serializer.validated_data.get('code', '')
        description = serializer.validated_data.get('description', '')
        embedding = embed_code_sync(code, description)
        
        serializer.save(
            tenant=tenant,
            created_by=self.request.user,
            embedding=embedding
        )
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search the library."""
        serializer = LibrarySearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        service = LibrarySearchService(str(tenant.id) if tenant else None)
        
        results = service.search(
            query=serializer.validated_data['query'],
            method=serializer.validated_data.get('method', 'hybrid'),
            item_type=serializer.validated_data.get('item_type'),
            language=serializer.validated_data.get('language'),
            category_id=serializer.validated_data.get('category_id'),
            limit=serializer.validated_data.get('limit', 20),
        )
        
        return Response({
            'count': len(results),
            'results': results,
        })
    
    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Record usage of a library item."""
        item = self.get_object()
        item.increment_usage()
        
        return Response({
            'message': 'Usage recorded',
            'usage_count': item.usage_count,
        })
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get version history for an item."""
        item = self.get_object()
        versions = item.versions.all()
        serializer = LibraryVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_version(self, request, pk=None):
        """Add a new version to an item."""
        item = self.get_object()
        
        version = request.data.get('version')
        code = request.data.get('code')
        changelog = request.data.get('changelog', '')
        
        if not version or not code:
            return Response(
                {'error': 'Version and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lib_version = LibraryVersion.objects.create(
            item=item,
            version=version,
            code=code,
            changelog=changelog,
            created_by=request.user,
        )
        
        # Update item code
        item.code = code
        item.embedding = embed_code_sync(code, item.description)
        item.save()
        
        serializer = LibraryVersionSerializer(lib_version)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def update_embedding(self, request, pk=None):
        """Regenerate embedding for an item."""
        item = self.get_object()
        
        embedding = embed_code_sync(item.code, item.description)
        
        if embedding:
            item.embedding = embedding
            item.save(update_fields=['embedding'])
            return Response({'message': 'Embedding updated'})
        
        return Response(
            {'error': 'Failed to generate embedding'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class ConstraintViewSet(TenantMixin, viewsets.ModelViewSet):
    """
    API viewset for constraints.
    """
    serializer_class = ConstraintSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        tenant = self.get_tenant()
        
        qs = Constraint.objects.filter(is_active=True)
        
        if tenant:
            qs = qs.filter(
                Q(tenant=tenant) | Q(tenant__isnull=True)
            )
        else:
            qs = qs.filter(tenant__isnull=True)
        
        # Filter by type
        constraint_type = self.request.query_params.get('type')
        if constraint_type:
            qs = qs.filter(constraint_type=constraint_type)
        
        return qs.order_by('-priority', 'name')
    
    def perform_create(self, serializer):
        tenant = self.get_tenant()
        serializer.save(tenant=tenant)
    
    @action(detail=False, methods=['post'])
    def sync_from_files(self, request):
        """Sync constraints from MD files."""
        tenant = self.get_tenant()
        
        loader = ConstraintLoader()
        result = loader.sync_to_database(
            tenant_id=str(tenant.id) if tenant else None
        )
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def for_generation(self, request):
        """Get constraints formatted for code generation."""
        from apps.ai_engine.v6.constraints import ConstraintManager
        
        tenant = self.get_tenant()
        language = request.query_params.get('language')
        item_type = request.query_params.get('item_type')
        
        manager = ConstraintManager(str(tenant.id) if tenant else None)
        prompt = manager.get_constraint_prompt(
            language=language,
            item_type=item_type
        )
        
        constraints = manager.get_applicable_constraints(
            language=language,
            item_type=item_type
        )
        
        return Response({
            'constraints': [c.name for c in constraints],
            'prompt': prompt,
        })


class CodeGenerationViewSet(TenantMixin, viewsets.ViewSet):
    """
    API viewset for code generation with research.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate code with library search, research, and constraints."""
        serializer = GenerateCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        
        # Build request
        gen_request = GenerationRequest(
            description=serializer.validated_data['description'],
            language=serializer.validated_data['language'],
            item_type=serializer.validated_data['item_type'],
            search_library=serializer.validated_data.get('search_library', True),
            do_research=serializer.validated_data.get('do_research', True),
            apply_constraints=serializer.validated_data.get('apply_constraints', True),
            save_to_library=serializer.validated_data.get('save_to_library', True),
            tenant_id=str(tenant.id) if tenant else None,
            user_id=str(request.user.id),
            existing_code=serializer.validated_data.get('existing_code'),
        )
        
        # Run pipeline (sync wrapper)
        import asyncio
        
        pipeline = CodeGenerationPipeline(gen_request.tenant_id)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(pipeline.run(gen_request))
        
        response_serializer = GenerateCodeResponseSerializer(data={
            'success': result.success,
            'code': result.code,
            'from_library': result.from_library,
            'library_item_id': result.library_item_id,
            'research_summary': result.research_summary or '',
            'constraints_applied': result.constraints_applied or [],
            'quality_score': result.quality_score,
            'error': result.error,
        })
        response_serializer.is_valid(raise_exception=True)
        
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def research(self, request):
        """Research a topic before generation."""
        serializer = ResearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = research_topic_sync(
            topic=serializer.validated_data['topic'],
            language=serializer.validated_data.get('language'),
            include_web=serializer.validated_data.get('include_web', True),
            include_github=serializer.validated_data.get('include_github', True),
            include_packages=serializer.validated_data.get('include_packages', True),
        )
        
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def search_first(self, request):
        """Search library first, return existing or generate new."""
        serializer = GenerateCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tenant = self.get_tenant()
        
        # Search library
        service = LibrarySearchService(str(tenant.id) if tenant else None)
        results = service.hybrid_search(
            query=serializer.validated_data['description'],
            item_type=serializer.validated_data['item_type'],
            language=serializer.validated_data['language'],
            limit=5
        )
        
        # Check for high-confidence match
        for result in results:
            if result.get('combined_score', 0) >= 0.85:
                try:
                    item = LibraryItem.objects.get(id=result['id'])
                    item.increment_usage()
                    
                    return Response({
                        'found_in_library': True,
                        'item_id': str(item.id),
                        'name': item.name,
                        'code': item.code,
                        'match_score': result['combined_score'],
                        'quality_score': item.quality_score,
                    })
                except LibraryItem.DoesNotExist:
                    pass
        
        # Return top suggestions if any
        return Response({
            'found_in_library': False,
            'suggestions': results[:3],
            'message': 'No high-confidence match found. Consider generating new code.',
        })







