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


class LibraryStatsView(viewsets.ViewSet):
    """
    Library statistics for Faibric admin.
    Shows component reuse, popular items, and cost savings.
    """
    permission_classes = []  # Open for admin access
    
    @action(detail=False, methods=['get'], url_path='overview')
    def overview(self, request):
        """Get library overview stats."""
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta
        
        total_items = LibraryItem.objects.filter(is_active=True).count()
        total_usage = LibraryItem.objects.aggregate(total=Sum('usage_count'))['total'] or 0
        
        # Top 10 most reused components
        top_reused = list(
            LibraryItem.objects.filter(is_active=True, usage_count__gt=0)
            .order_by('-usage_count')
            .values('id', 'name', 'item_type', 'usage_count', 'quality_score', 'keywords')[:10]
        )
        
        # Recent additions (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_items = LibraryItem.objects.filter(created_at__gte=week_ago).count()
        
        # Usage by type
        usage_by_type = list(
            LibraryItem.objects.filter(is_active=True)
            .values('item_type')
            .annotate(count=Count('id'), total_usage=Sum('usage_count'))
            .order_by('-total_usage')
        )
        
        # Estimated cost savings (rough: each reuse saves ~$0.05 in API calls)
        estimated_savings = total_usage * 0.05
        
        return Response({
            'total_items': total_items,
            'total_reuses': total_usage,
            'estimated_cost_savings_usd': round(estimated_savings, 2),
            'new_items_this_week': recent_items,
            'top_reused_components': top_reused,
            'usage_by_type': usage_by_type,
        })
    
    @action(detail=False, methods=['get'], url_path='items')
    def all_items(self, request):
        """List all library items with full details for admin."""
        items = LibraryItem.objects.filter(is_active=True).order_by('-usage_count', '-created_at')
        
        return Response({
            'count': items.count(),
            'items': [
                {
                    'id': str(item.id),
                    'name': item.name,
                    'item_type': item.item_type,
                    'language': item.language,
                    'usage_count': item.usage_count,
                    'quality_score': item.quality_score,
                    'keywords': item.keywords,
                    'description': item.description[:200] if item.description else '',
                    'code_preview': item.code[:500] if item.code else '',
                    'last_used_at': item.last_used_at,
                    'created_at': item.created_at,
                    'source': item.source,
                }
                for item in items
            ]
        })
    
    @action(detail=True, methods=['get'], url_path='detail')
    def item_detail(self, request, pk=None):
        """Get full details of a specific library item."""
        try:
            item = LibraryItem.objects.get(id=pk)
            return Response({
                'id': str(item.id),
                'name': item.name,
                'slug': item.slug,
                'item_type': item.item_type,
                'language': item.language,
                'code': item.code,
                'description': item.description,
                'usage_example': item.usage_example,
                'documentation': item.documentation,
                'keywords': item.keywords,
                'tags': item.tags,
                'dependencies': item.dependencies,
                'quality_score': item.quality_score,
                'usage_count': item.usage_count,
                'last_used_at': item.last_used_at,
                'source': item.source,
                'is_public': item.is_public,
                'created_at': item.created_at,
                'updated_at': item.updated_at,
            })
        except LibraryItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=404)


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


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def instruction_log_view(request):
    """
    View the instruction-based solutions log.
    
    This shows all detected instruction-based solutions that need enforcement.
    """
    from .instruction_log import get_instruction_log
    from .models import InstructionSolutionRecord
    
    log = get_instruction_log()
    
    # Get from database for accuracy
    try:
        pending = InstructionSolutionRecord.objects.filter(status='pending').order_by('-detected_at')
        all_records = InstructionSolutionRecord.objects.all().order_by('-detected_at')
        
        pending_data = [
            {
                'id': r.id,
                'detected_at': r.detected_at.isoformat(),
                'file_path': r.file_path,
                'line_number': r.line_number,
                'instruction_text': r.instruction_text[:200],
                'missing_enforcement': r.missing_enforcement,
                'status': r.status,
            }
            for r in pending[:20]
        ]
        
        return Response({
            'total': all_records.count(),
            'pending': pending.count(),
            'pending_items': pending_data,
            'message': 'Instruction-based solutions that need code enforcement',
        })
    except Exception as e:
        # Fallback to in-memory log
        return Response({
            'summary': log.get_summary(),
            'error': str(e),
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_instruction_fixed(request, entry_id):
    """Mark an instruction-based solution as fixed."""
    from .instruction_log import get_instruction_log
    
    fixed_by = request.data.get('fixed_by', 'unknown')
    log = get_instruction_log()
    
    success = log.mark_fixed(entry_id, fixed_by)
    
    if success:
        return Response({'success': True, 'message': f'Entry {entry_id} marked as fixed'})
    else:
        return Response({'success': False, 'message': 'Entry not found'}, status=404)


@api_view(['GET'])
@permission_classes([AllowAny])
def alerts_view(request):
    """
    View all unread alerts.
    
    This is the main notification endpoint - check this to see new alerts.
    """
    from .models import Alert
    
    try:
        unread = Alert.objects.filter(is_read=False).order_by('-created_at')
        all_alerts = Alert.objects.all().order_by('-created_at')[:50]
        
        unread_data = [
            {
                'id': a.id,
                'created_at': a.created_at.isoformat(),
                'type': a.alert_type,
                'title': a.title,
                'message': a.message[:500],
                'severity': a.severity,
            }
            for a in unread[:20]
        ]
        
        return Response({
            'unread_count': unread.count(),
            'total_count': all_alerts.count(),
            'unread_alerts': unread_data,
            'check_url': '/api/library/alerts/',
        })
    except Exception as e:
        return Response({
            'error': str(e),
            'unread_count': 0,
            'unread_alerts': [],
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_alert_read(request, alert_id):
    """Mark an alert as read."""
    from .models import Alert
    from datetime import datetime
    
    try:
        alert = Alert.objects.get(id=alert_id)
        alert.is_read = True
        alert.read_at = datetime.now()
        alert.save()
        return Response({'success': True})
    except Alert.DoesNotExist:
        return Response({'success': False, 'message': 'Alert not found'}, status=404)


@api_view(['POST'])
@permission_classes([AllowAny])
def regenerate_library(request):
    """
    Regenerate the component library with high-quality components.
    
    This clears all existing components and creates new, production-ready ones.
    """
    from .models import LibraryItem
    
    # Secret key check for security
    secret = request.data.get('secret') or request.query_params.get('secret')
    if secret != 'faibric_regenerate_2026':
        return Response({'error': 'Invalid secret'}, status=403)
    
    try:
        # Clear existing
        existing_count = LibraryItem.objects.count()
        LibraryItem.objects.all().delete()
        
        # Define components - include ALL types to prevent AI generation
        COMPONENTS = {
            # Layout component - CRITICAL
            "layout_app": {
                "name": "LayoutApp",
                "description": "Main app layout wrapper with navigation slots",
                "code": '''
// v2-no-template-literals
const LayoutApp = ({ children, currentView, onNavigate, brandName = "Brand" }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <NavigationHeader currentView={currentView} onNavigate={onNavigate} brandName={brandName} />
      <main className="container mx-auto px-4 py-8">
        {children}
      </main>
    </div>
  );
};
''',
                "keywords": ["layout", "app", "wrapper"],
                "tags": ["layout", "app"],
            },
            "navigation_header": {
                "name": "NavigationHeader",
                "description": "A responsive navigation header with logo and menu items",
                "code": '''
const NavigationHeader = ({ currentView, onNavigate, brandName = "Brand" }) => {
  const navItems = [
    { id: "home", label: "Home" },
    { id: "services", label: "Services" },
    { id: "about", label: "About" },
    { id: "contact", label: "Contact" },
    { id: "settings", label: "Settings" },
  ];

  return (
    <nav className="bg-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <span className="text-2xl font-bold text-blue-600">{brandName}</span>
          </div>
          <div className="flex items-center space-x-4">
            {navItems.map((item) => (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={"px-3 py-2 rounded-md text-sm font-medium transition-colors " + (currentView === item.id ? "bg-blue-100 text-blue-700" : "text-gray-600 hover:text-blue-600 hover:bg-gray-50")}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};
''',
                "keywords": ["navigation", "header", "navbar", "menu"],
                "tags": ["navigation", "header"],
            },
            "hero_gradient": {
                "name": "HeroGradient",
                "description": "A hero section with gradient background and call-to-action",
                "code": '''
const HeroGradient = ({ 
  title = "Welcome to Our Service",
  subtitle = "We provide professional solutions tailored to your needs",
  ctaText = "Get Started",
  onCtaClick
}) => {
  return (
    <section className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white">
      <div className="absolute inset-0 bg-black opacity-10"></div>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 lg:py-32">
        <div className="text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight mb-6">
            {title}
          </h1>
          <p className="text-xl md:text-2xl text-blue-100 max-w-3xl mx-auto mb-10">
            {subtitle}
          </p>
          <button
            onClick={onCtaClick}
            className="inline-flex items-center px-8 py-4 text-lg font-semibold rounded-lg bg-white text-blue-600 hover:bg-blue-50 transition-all transform hover:scale-105 shadow-xl"
          >
            {ctaText}
          </button>
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["hero", "gradient", "landing", "cta", "banner"],
                "tags": ["hero", "gradient"],
            },
            "services_grid": {
                "name": "ServicesGrid",
                "description": "A grid of service cards with icons and descriptions",
                "code": '''
const ServicesGrid = ({ services }) => {
  const defaultServices = [
    { title: "Consultation", description: "Expert advice tailored to your needs" },
    { title: "Custom Solutions", description: "Personalized strategies for your situation" },
    { title: "Ongoing Support", description: "Continuous assistance for your success" },
    { title: "Expert Advice", description: "Professional guidance from specialists" }
  ];
  const items = services || defaultServices;

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Our Services</h2>
        <div className="grid md:grid-cols-4 gap-8">
          {items.map((service, i) => (
            <div key={i} className="bg-white rounded-xl shadow-md hover:shadow-xl p-6 text-center">
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-blue-600 text-xl font-bold">{i + 1}</span>
              </div>
              <h3 className="text-xl font-semibold mb-2">{service.title}</h3>
              <p className="text-gray-600">{service.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["services", "grid", "cards", "features"],
                "tags": ["services", "grid"],
            },
            "about_section": {
                "name": "AboutSection",
                "description": "An about section with company info",
                "code": '''
const AboutSection = ({ title = "About Us", description }) => {
  const defaultDesc = "We are dedicated professionals with years of experience. Our commitment to excellence drives everything we do.";
  return (
    <section className="py-16 bg-white">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h2 className="text-3xl font-bold mb-6">{title}</h2>
        <p className="text-lg text-gray-600">{description || defaultDesc}</p>
      </div>
    </section>
  );
};
''',
                "keywords": ["about", "company", "mission"],
                "tags": ["about", "section"],
            },
            "contact_form": {
                "name": "ContactForm",
                "description": "A contact form with validation",
                "code": '''
const ContactForm = ({ onSubmit, title = "Contact Us" }) => {
  const [formData, setFormData] = React.useState({ name: "", email: "", message: "" });
  const [submitted, setSubmitted] = React.useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) onSubmit(formData);
    setSubmitted(true);
    setTimeout(() => { setSubmitted(false); setFormData({ name: "", email: "", message: "" }); }, 3000);
  };

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-8">{title}</h2>
        {submitted && <div className="mb-4 p-4 bg-green-100 text-green-700 rounded">Thank you! We will contact you soon.</div>}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-lg p-8 space-y-6">
          <div>
            <label className="block text-sm font-medium mb-2">Name</label>
            <input type="text" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full px-4 py-3 border rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Email</label>
            <input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-4 py-3 border rounded-lg" required />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Message</label>
            <textarea value={formData.message} onChange={(e) => setFormData({...formData, message: e.target.value})}
              rows={4} className="w-full px-4 py-3 border rounded-lg" required />
          </div>
          <button type="submit" className="w-full py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700">
            Send Message
          </button>
        </form>
      </div>
    </section>
  );
};
''',
                "keywords": ["contact", "form", "email"],
                "tags": ["contact", "form"],
            },
            "footer_simple": {
                "name": "FooterSimple",
                "description": "A simple footer with links",
                "code": '''
const FooterSimple = ({ brandName = "Brand" }) => {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="max-w-7xl mx-auto px-4 text-center">
        <span className="text-2xl font-bold text-blue-400">{brandName}</span>
        <p className="mt-4 text-gray-400">Providing quality services. Built with Faibric.</p>
        <p className="mt-4 text-gray-500 text-sm">&copy; {new Date().getFullYear()} {brandName}. All rights reserved.</p>
      </div>
    </footer>
  );
};
''',
                "keywords": ["footer", "copyright", "links"],
                "tags": ["footer", "simple"],
            },
            "settings_view": {
                "name": "SettingsView",
                "description": "A settings page with configuration options",
                "code": '''
const SettingsView = () => {
  const [settings, setSettings] = React.useState({ notifications: true, darkMode: false, language: "en" });
  return (
    <section className="py-8">
      <div className="max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold mb-6">Settings</h2>
        <div className="bg-white rounded-xl shadow-md">
          <div className="p-6 border-b flex justify-between items-center">
            <div><h3 className="font-medium">Notifications</h3><p className="text-sm text-gray-500">Receive updates</p></div>
            <button onClick={() => setSettings({...settings, notifications: !settings.notifications})}
              className={"w-12 h-6 rounded-full " + (settings.notifications ? "bg-blue-600" : "bg-gray-300")}>
              <span className={"block w-5 h-5 bg-white rounded-full transform transition " + (settings.notifications ? "translate-x-6" : "translate-x-0.5")} />
            </button>
          </div>
          <div className="p-6 flex justify-between items-center">
            <div><h3 className="font-medium">Language</h3><p className="text-sm text-gray-500">Select language</p></div>
            <select value={settings.language} onChange={(e) => setSettings({...settings, language: e.target.value})}
              className="px-4 py-2 border rounded-lg">
              <option value="en">English</option><option value="es">Spanish</option>
            </select>
          </div>
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["settings", "preferences", "config"],
                "tags": ["settings", "view"],
            },
            "dashboard_stats": {
                "name": "DashboardStats",
                "description": "Dashboard with stats cards",
                "code": '''
const DashboardStats = ({ stats }) => {
  const defaultStats = [
    { label: "Users", value: "1,234", change: "+12%" },
    { label: "Revenue", value: "$45K", change: "+8%" },
    { label: "Orders", value: "567", change: "-3%" },
    { label: "Rate", value: "3.2%", change: "+0.5%" }
  ];
  const items = stats || defaultStats;

  return (
    <section className="py-8">
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid md:grid-cols-4 gap-6">
        {items.map((stat, i) => (
          <div key={i} className="bg-white rounded-xl shadow-md p-6">
            <p className="text-sm text-gray-500">{stat.label}</p>
            <p className="text-3xl font-bold">{stat.value}</p>
            <span className={"text-sm " + (stat.change.startsWith("+") ? "text-green-600" : "text-red-600")}>{stat.change}</span>
          </div>
        ))}
      </div>
    </section>
  );
};
''',
                "keywords": ["dashboard", "stats", "analytics"],
                "tags": ["dashboard", "stats"],
            },
            "pricing_table": {
                "name": "PricingTable",
                "description": "Pricing table with tiers",
                "code": '''
const PricingTable = ({ onSelectPlan }) => {
  const plans = [
    { name: "Starter", price: "29", features: ["5 Projects", "Basic Support", "1GB Storage"], popular: false },
    { name: "Pro", price: "79", features: ["Unlimited", "Priority Support", "10GB Storage", "Analytics"], popular: true },
    { name: "Enterprise", price: "199", features: ["Everything", "Dedicated Support", "Unlimited Storage", "SSO"], popular: false }
  ];

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Pricing</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {plans.map((plan, i) => (
            <div key={i} className={"bg-white rounded-2xl shadow-lg p-8 " + (plan.popular ? "ring-2 ring-blue-600" : "")}>
              {plan.popular && <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">Popular</span>}
              <h3 className="text-xl font-bold mt-2">{plan.name}</h3>
              <div className="my-4"><span className="text-4xl font-bold">${plan.price}</span>/mo</div>
              <ul className="space-y-2 mb-6">
                {plan.features.map((f, j) => <li key={j} className="text-gray-600">* {f}</li>)}
              </ul>
              <button onClick={() => onSelectPlan && onSelectPlan(plan)}
                className={"w-full py-3 rounded-lg font-semibold " + (plan.popular ? "bg-blue-600 text-white" : "bg-gray-100")}>
                Get Started
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["pricing", "plans", "subscription"],
                "tags": ["pricing", "table"],
            },
            "testimonials_carousel": {
                "name": "TestimonialsCarousel",
                "description": "Testimonials with reviews",
                "code": '''
const TestimonialsCarousel = () => {
  const [active, setActive] = React.useState(0);
  const items = [
    { name: "Sarah J.", role: "CEO", content: "Amazing service! Highly recommend." },
    { name: "Mike C.", role: "Founder", content: "Professional and delivered beyond expectations." },
    { name: "Emily D.", role: "Director", content: "Transformed our vision into reality." }
  ];

  return (
    <section className="py-16 bg-blue-50">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">What Clients Say</h2>
        <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
          <p className="text-xl italic mb-6">"{items[active].content}"</p>
          <p className="font-semibold">{items[active].name}</p>
          <p className="text-gray-500">{items[active].role}</p>
          <div className="flex justify-center mt-6 space-x-2">
            {items.map((_, i) => (
              <button key={i} onClick={() => setActive(i)}
                className={"w-3 h-3 rounded-full " + (i === active ? "bg-blue-600" : "bg-gray-300")} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["testimonials", "reviews", "clients"],
                "tags": ["testimonials", "carousel"],
            },
            # Additional essential types to prevent AI generation
            "feature_grid": {
                "name": "FeatureGrid",
                "description": "Feature showcase grid",
                "code": '''
const FeatureGrid = ({ features }) => {
  const defaultFeatures = [
    { title: "Fast", description: "Lightning quick performance" },
    { title: "Secure", description: "Enterprise-grade security" },
    { title: "Reliable", description: "99.9% uptime guarantee" },
    { title: "Scalable", description: "Grows with your needs" }
  ];
  const items = features || defaultFeatures;
  return (
    <section className="py-16">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">Features</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {items.map((f, i) => (
            <div key={i} className="text-center p-6">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <span className="text-blue-600 font-bold">{i + 1}</span>
              </div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-600">{f.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["feature", "grid", "showcase"],
                "tags": ["feature", "grid"],
            },
            "cta_centered": {
                "name": "CallToAction",
                "description": "Call to action section",
                "code": '''
const CallToAction = ({ headline = "Ready to Get Started?", buttonText = "Contact Us", onCtaClick }) => {
  return (
    <section className="py-16 bg-blue-600 text-white">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <h2 className="text-3xl font-bold mb-6">{headline}</h2>
        <p className="text-blue-100 mb-8">Join thousands of satisfied customers today.</p>
        <button onClick={onCtaClick} className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50">
          {buttonText}
        </button>
      </div>
    </section>
  );
};
''',
                "keywords": ["cta", "call", "action", "centered"],
                "tags": ["cta", "centered"],
            },
            "chart_simple": {
                "name": "ChartSection",
                "description": "Simple chart display",
                "code": '''
const ChartSection = ({ data, title = "Statistics" }) => {
  const defaultData = [
    { label: "Jan", value: 40 },
    { label: "Feb", value: 60 },
    { label: "Mar", value: 45 },
    { label: "Apr", value: 80 },
    { label: "May", value: 65 }
  ];
  const items = data || defaultData;
  const maxValue = Math.max(...items.map(d => d.value));
  return (
    <section className="py-8">
      <h3 className="text-xl font-bold mb-6">{title}</h3>
      <div className="bg-white rounded-xl shadow p-6">
        <div className="flex items-end justify-between h-48 gap-4">
          {items.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div className="w-full bg-blue-500 rounded-t" style={{ height: `${(d.value / maxValue) * 100}%` }} />
              <span className="text-sm text-gray-500 mt-2">{d.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["chart", "simple", "bar", "stats"],
                "tags": ["chart", "simple"],
            },
            "table_data": {
                "name": "DataTable",
                "description": "Data table with sorting",
                "code": '''
const DataTable = ({ data, columns }) => {
  const defaultColumns = [{ key: "name", label: "Name" }, { key: "value", label: "Value" }, { key: "status", label: "Status" }];
  const defaultData = [
    { name: "Item A", value: "$100", status: "Active" },
    { name: "Item B", value: "$250", status: "Pending" },
    { name: "Item C", value: "$75", status: "Active" }
  ];
  const cols = columns || defaultColumns;
  const rows = data || defaultData;
  return (
    <section className="py-8">
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              {cols.map(c => <th key={c.key} className="px-6 py-3 text-left text-sm font-medium text-gray-500">{c.label}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row, i) => (
              <tr key={i}>
                {cols.map(c => <td key={c.key} className="px-6 py-4 text-sm">{row[c.key]}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};
''',
                "keywords": ["table", "data", "list"],
                "tags": ["table", "data"],
            },
            "list_items": {
                "name": "ListView",
                "description": "List view with items",
                "code": '''
const ListView = ({ items, title = "Items" }) => {
  const defaultItems = [
    { title: "Item 1", description: "Description for item 1" },
    { title: "Item 2", description: "Description for item 2" },
    { title: "Item 3", description: "Description for item 3" }
  ];
  const data = items || defaultItems;
  return (
    <section className="py-8">
      <h3 className="text-xl font-bold mb-6">{title}</h3>
      <div className="space-y-4">
        {data.map((item, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4 flex items-center">
            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-4">
              <span className="text-blue-600 font-bold">{i + 1}</span>
            </div>
            <div>
              <h4 className="font-medium">{item.title}</h4>
              <p className="text-sm text-gray-500">{item.description}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
''',
                "keywords": ["list", "items", "view"],
                "tags": ["list", "items"],
            },
            "gallery_grid": {
                "name": "Gallery",
                "description": "Image gallery grid",
                "code": '''
const Gallery = ({ images, title = "Gallery" }) => {
  const defaultImages = [
    { src: "https://picsum.photos/400/300?1", alt: "Image 1" },
    { src: "https://picsum.photos/400/300?2", alt: "Image 2" },
    { src: "https://picsum.photos/400/300?3", alt: "Image 3" },
    { src: "https://picsum.photos/400/300?4", alt: "Image 4" }
  ];
  const items = images || defaultImages;
  return (
    <section className="py-8">
      <h3 className="text-xl font-bold mb-6">{title}</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {items.map((img, i) => (
          <div key={i} className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
            <img src={img.src} alt={img.alt} className="w-full h-full object-cover" />
          </div>
        ))}
      </div>
    </section>
  );
};
''',
                "keywords": ["gallery", "grid", "images"],
                "tags": ["gallery", "grid"],
            },
            "stats_cards": {
                "name": "StatsCards",
                "description": "Statistics cards display",
                "code": '''
const StatsCards = ({ stats }) => {
  const defaultStats = [
    { label: "Users", value: "10K+" },
    { label: "Projects", value: "500+" },
    { label: "Countries", value: "50+" },
    { label: "Rating", value: "4.9" }
  ];
  const items = stats || defaultStats;
  return (
    <section className="py-8">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {items.map((stat, i) => (
          <div key={i} className="bg-white rounded-xl shadow p-6 text-center">
            <p className="text-3xl font-bold text-blue-600">{stat.value}</p>
            <p className="text-gray-500 mt-1">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
};
''',
                "keywords": ["stats", "cards", "numbers"],
                "tags": ["stats", "cards"],
            },
            # Variant duplicates to match decomposer requests
            "hero_full": {
                "name": "HeroFull",
                "description": "Full-width hero section",
                "code": '''
const HeroFull = ({ title = "Welcome", subtitle = "Your trusted partner", onCtaClick }) => (
  <section className="bg-gradient-to-r from-blue-600 to-blue-800 text-white py-24">
    <div className="max-w-4xl mx-auto px-4 text-center">
      <h1 className="text-5xl font-bold mb-6">{title}</h1>
      <p className="text-xl text-blue-100 mb-10">{subtitle}</p>
      <button onClick={onCtaClick} className="px-8 py-4 bg-white text-blue-600 font-semibold rounded-lg hover:bg-blue-50">
        Get Started
      </button>
    </div>
  </section>
);
''',
                "keywords": ["hero", "full", "landing", "banner"],
                "tags": ["hero", "full"],
            },
            "footer_full": {
                "name": "FooterFull",
                "description": "Full footer with links",
                "code": '''
const FooterFull = ({ brandName = "Brand" }) => (
  <footer className="bg-gray-900 text-white py-12">
    <div className="max-w-6xl mx-auto px-4">
      <div className="grid md:grid-cols-3 gap-8">
        <div>
          <span className="text-xl font-bold text-blue-400">{brandName}</span>
          <p className="mt-4 text-gray-400">Providing quality services.</p>
        </div>
        <div>
          <h4 className="font-semibold mb-4">Links</h4>
          <ul className="space-y-2 text-gray-400">
            <li><a href="#" className="hover:text-white">Home</a></li>
            <li><a href="#" className="hover:text-white">About</a></li>
            <li><a href="#" className="hover:text-white">Contact</a></li>
          </ul>
        </div>
        <div>
          <h4 className="font-semibold mb-4">Contact</h4>
          <p className="text-gray-400">contact@example.com</p>
        </div>
      </div>
      <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-500">
        Built with Faibric
      </div>
    </div>
  </footer>
);
''',
                "keywords": ["footer", "full", "links"],
                "tags": ["footer", "full"],
            },
            "form_default": {
                "name": "FormSection",
                "description": "Generic form section",
                "code": '''
const FormSection = ({ title = "Form", onSubmit }) => {
  const [data, setData] = React.useState({ name: "", email: "" });
  const handleSubmit = (e) => { e.preventDefault(); onSubmit && onSubmit(data); };
  return (
    <section className="py-8">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow p-6">
        <h3 className="text-xl font-bold mb-4">{title}</h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="text" placeholder="Name" value={data.name} onChange={(e) => setData({...data, name: e.target.value})} className="w-full px-4 py-2 border rounded" />
          <input type="email" placeholder="Email" value={data.email} onChange={(e) => setData({...data, email: e.target.value})} className="w-full px-4 py-2 border rounded" />
          <button type="submit" className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Submit</button>
        </form>
      </div>
    </section>
  );
};
''',
                "keywords": ["form", "default", "input"],
                "tags": ["form", "default"],
            },
            # ═══════════════════════════════════════════════════════════════
            # PHASE 2: Advanced Components (added for better reuse)
            # ═══════════════════════════════════════════════════════════════
            "crypto_tracker": {
                "name": "CryptoTracker",
                "description": "Live cryptocurrency price tracker with real API data",
                "code": '''
const CryptoTracker = ({ coins = ["bitcoin", "ethereum", "solana"], refreshInterval = 30000 }) => {
  const [prices, setPrices] = React.useState({});
  const [loading, setLoading] = React.useState(true);
  const [lastUpdated, setLastUpdated] = React.useState(null);

  const fetchPrices = async () => {
    try {
      const response = await fetch("https://api.faibric.com/api/gateway/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: "coingecko",
          endpoint: "/simple/price?ids=" + coins.join(",") + "&vs_currencies=usd&include_24hr_change=true"
        })
      });
      const result = await response.json();
      setPrices(result.data || result);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Fetch error:", err);
    }
    setLoading(false);
  };

  React.useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, refreshInterval);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Crypto Prices</h2>
        {lastUpdated && <span className="text-sm text-gray-500">Updated: {lastUpdated}</span>}
      </div>
      <div className="grid md:grid-cols-3 gap-6">
        {loading ? (
          [1, 2, 3].map(i => (
            <div key={i} className="bg-white rounded-xl shadow p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-24 mb-4"></div>
              <div className="h-8 bg-gray-200 rounded w-32"></div>
            </div>
          ))
        ) : (
          Object.entries(prices).map(([coin, data]) => (
            <div key={coin} className="bg-white rounded-xl shadow-md p-6">
              <p className="text-gray-500 capitalize mb-2">{coin}</p>
              <p className="text-3xl font-bold">${data.usd ? data.usd.toLocaleString() : "---"}</p>
              {data.usd_24h_change && (
                <span className={"text-sm " + (data.usd_24h_change >= 0 ? "text-green-600" : "text-red-600")}>
                  {data.usd_24h_change >= 0 ? "+" : ""}{data.usd_24h_change.toFixed(2)}%
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  );
};
''',
                "keywords": ["crypto", "tracker", "bitcoin", "prices", "live", "real-time", "data_fetcher"],
                "tags": ["data_fetcher", "crypto"],  # PHASE 3: Maps to DATA_FETCHER/crypto requirement
            },
            "faq_accordion": {
                "name": "FAQAccordion",
                "description": "FAQ section with expandable accordion items",
                "code": '''
const FAQAccordion = ({ faqs, title = "Frequently Asked Questions" }) => {
  const [openIndex, setOpenIndex] = React.useState(null);
  const defaultFaqs = [
    { question: "How do I get started?", answer: "Getting started is easy. Simply sign up and follow our quick setup guide." },
    { question: "What payment methods do you accept?", answer: "We accept all major credit cards, PayPal, and bank transfers." },
    { question: "Can I cancel my subscription?", answer: "Yes, you can cancel anytime. No questions asked." },
    { question: "Do you offer support?", answer: "Yes, we offer 24/7 customer support via chat, email, and phone." }
  ];
  const items = faqs || defaultFaqs;

  return (
    <section className="py-16 bg-gray-50">
      <div className="max-w-3xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">{title}</h2>
        <div className="space-y-4">
          {items.map((faq, i) => (
            <div key={i} className="bg-white rounded-xl shadow-md overflow-hidden">
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="w-full px-6 py-4 text-left flex justify-between items-center"
              >
                <span className="font-medium">{faq.question}</span>
                <span className={"transform transition-transform " + (openIndex === i ? "rotate-180" : "")}>
                  [V]
                </span>
              </button>
              {openIndex === i && (
                <div className="px-6 pb-4 text-gray-600">{faq.answer}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["faq", "accordion", "questions", "help", "support", "list"],
                "tags": ["list", "faq"],  # PHASE 3: Maps to LIST requirement
            },
            "team_grid": {
                "name": "TeamGrid",
                "description": "Team members display grid with photos and roles",
                "code": '''
const TeamGrid = ({ members, title = "Our Team" }) => {
  const defaultMembers = [
    { name: "Sarah Johnson", role: "CEO & Founder", image: "https://i.pravatar.cc/200?img=1" },
    { name: "Michael Chen", role: "CTO", image: "https://i.pravatar.cc/200?img=2" },
    { name: "Emily Davis", role: "Head of Design", image: "https://i.pravatar.cc/200?img=3" },
    { name: "James Wilson", role: "Lead Developer", image: "https://i.pravatar.cc/200?img=4" }
  ];
  const team = members || defaultMembers;

  return (
    <section className="py-16">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-bold text-center mb-12">{title}</h2>
        <div className="grid md:grid-cols-4 gap-8">
          {team.map((member, i) => (
            <div key={i} className="text-center">
              <div className="w-32 h-32 mx-auto mb-4 rounded-full overflow-hidden bg-gray-200">
                <img src={member.image} alt={member.name} className="w-full h-full object-cover" />
              </div>
              <h3 className="font-semibold text-lg">{member.name}</h3>
              <p className="text-gray-500">{member.role}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
''',
                "keywords": ["team", "members", "staff", "people", "about", "gallery"],
                "tags": ["gallery", "team"],  # PHASE 3: Maps to GALLERY requirement
            },
            "sidebar_nav": {
                "name": "SidebarNav",
                "description": "Dashboard sidebar navigation with icons",
                "code": '''
const SidebarNav = ({ currentView, onNavigate, brandName = "Dashboard" }) => {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: "[D]" },
    { id: "analytics", label: "Analytics", icon: "[A]" },
    { id: "users", label: "Users", icon: "[U]" },
    { id: "reports", label: "Reports", icon: "[R]" },
    { id: "settings", label: "Settings", icon: "[S]" }
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen">
      <div className="p-6">
        <span className="text-xl font-bold">{brandName}</span>
      </div>
      <nav className="mt-6">
        {navItems.map(item => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={"w-full flex items-center px-6 py-3 text-left transition-colors " + (currentView === item.id ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800")}
          >
            <span className="mr-3">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
};
''',
                "keywords": ["sidebar", "navigation", "dashboard", "menu"],
                "tags": ["navigation", "sidebar"],  # PHASE 3: Maps to NAVIGATION/sidebar
            },
            "activity_feed": {
                "name": "ActivityFeed",
                "description": "Recent activity feed with timestamps",
                "code": '''
const ActivityFeed = ({ activities, title = "Recent Activity" }) => {
  const defaultActivities = [
    { user: "John", action: "created a new project", time: "2 min ago", type: "create" },
    { user: "Sarah", action: "updated settings", time: "15 min ago", type: "update" },
    { user: "Mike", action: "deleted a file", time: "1 hour ago", type: "delete" },
    { user: "Emily", action: "invited a team member", time: "3 hours ago", type: "invite" }
  ];
  const items = activities || defaultActivities;
  const typeColors = { create: "bg-green-500", update: "bg-blue-500", delete: "bg-red-500", invite: "bg-purple-500" };

  return (
    <section className="py-8">
      <h3 className="text-xl font-bold mb-6">{title}</h3>
      <div className="bg-white rounded-xl shadow-md divide-y">
        {items.map((activity, i) => (
          <div key={i} className="p-4 flex items-center">
            <div className={"w-2 h-2 rounded-full mr-4 " + (typeColors[activity.type] || "bg-gray-500")}></div>
            <div className="flex-1">
              <p><span className="font-medium">{activity.user}</span> {activity.action}</p>
              <p className="text-sm text-gray-500">{activity.time}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
''',
                "keywords": ["activity", "feed", "timeline", "recent", "log", "list"],
                "tags": ["list", "activity"],  # PHASE 3: Maps to LIST requirement
            },
            "loading_skeleton": {
                "name": "LoadingSkeleton",
                "description": "Loading skeleton placeholder for content",
                "code": '''
const LoadingSkeleton = ({ rows = 3, type = "card" }) => {
  if (type === "table") {
    return (
      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        <div className="p-4 border-b bg-gray-50">
          <div className="flex gap-4">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-4 bg-gray-200 rounded flex-1 animate-pulse"></div>)}
          </div>
        </div>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 border-b">
            <div className="flex gap-4">
              {[1, 2, 3, 4].map(j => <div key={j} className="h-4 bg-gray-100 rounded flex-1 animate-pulse"></div>)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="bg-white rounded-xl shadow-md p-6 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-100 rounded w-1/2"></div>
        </div>
      ))}
    </div>
  );
};
''',
                "keywords": ["loading", "skeleton", "placeholder", "shimmer"],
                "tags": ["loading", "skeleton"],
            },
            "empty_state": {
                "name": "EmptyState",
                "description": "Empty state placeholder with icon and action",
                "code": '''
const EmptyState = ({ title = "No data yet", description = "Get started by adding your first item.", actionText = "Add Item", onAction }) => {
  return (
    <div className="text-center py-16">
      <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <span className="text-2xl text-gray-400">[+]</span>
      </div>
      <h3 className="text-xl font-semibold text-gray-700 mb-2">{title}</h3>
      <p className="text-gray-500 mb-6 max-w-sm mx-auto">{description}</p>
      {onAction && (
        <button onClick={onAction} className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700">
          {actionText}
        </button>
      )}
    </div>
  );
};
''',
                "keywords": ["empty", "state", "placeholder", "no-data"],
                "tags": ["empty", "state"],
            },
            "tabs_container": {
                "name": "TabsContainer",
                "description": "Tab navigation container with content panels",
                "code": '''
const TabsContainer = ({ tabs, defaultTab }) => {
  const defaultTabs = [
    { id: "overview", label: "Overview", content: "Overview content goes here." },
    { id: "details", label: "Details", content: "Details content goes here." },
    { id: "settings", label: "Settings", content: "Settings content goes here." }
  ];
  const items = tabs || defaultTabs;
  const [activeTab, setActiveTab] = React.useState(defaultTab || items[0]?.id);

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      <div className="flex border-b">
        {items.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={"px-6 py-4 font-medium transition-colors " + (activeTab === tab.id ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500 hover:text-gray-700")}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="p-6">
        {items.find(t => t.id === activeTab)?.content}
      </div>
    </div>
  );
};
''',
                "keywords": ["tabs", "container", "panels", "navigation"],
                "tags": ["tabs", "container"],
            },
            "modal_dialog": {
                "name": "ModalDialog",
                "description": "Modal dialog overlay with content",
                "code": '''
const ModalDialog = ({ isOpen, onClose, title = "Dialog", children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose}></div>
      <div className="relative bg-white rounded-xl shadow-2xl max-w-md w-full mx-4">
        <div className="flex justify-between items-center p-6 border-b">
          <h3 className="text-xl font-semibold">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">[X]</button>
        </div>
        <div className="p-6">{children}</div>
        <div className="flex justify-end gap-4 p-6 border-t">
          <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:text-gray-800">Cancel</button>
          <button onClick={onClose} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Confirm</button>
        </div>
      </div>
    </div>
  );
};
''',
                "keywords": ["modal", "dialog", "popup", "overlay"],
                "tags": ["modal", "dialog"],
            },
            "notification_banner": {
                "name": "NotificationBanner",
                "description": "Notification banner with dismiss action",
                "code": '''
const NotificationBanner = ({ type = "info", message = "This is a notification.", onDismiss }) => {
  const colors = {
    info: "bg-blue-50 text-blue-800 border-blue-200",
    success: "bg-green-50 text-green-800 border-green-200",
    warning: "bg-yellow-50 text-yellow-800 border-yellow-200",
    error: "bg-red-50 text-red-800 border-red-200"
  };

  return (
    <div className={"p-4 rounded-lg border flex justify-between items-center " + colors[type]}>
      <div className="flex items-center">
        <span className="mr-3">[!]</span>
        <p>{message}</p>
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="text-current opacity-50 hover:opacity-100">[X]</button>
      )}
    </div>
  );
};
''',
                "keywords": ["notification", "banner", "alert", "message"],
                "tags": ["notification", "banner"],
            },
            "search_header": {
                "name": "SearchHeader",
                "description": "Search header with filters",
                "code": '''
const SearchHeader = ({ onSearch, placeholder = "Search...", filters = [] }) => {
  const [query, setQuery] = React.useState("");
  const [activeFilter, setActiveFilter] = React.useState("all");
  const defaultFilters = [
    { id: "all", label: "All" },
    { id: "recent", label: "Recent" },
    { id: "popular", label: "Popular" }
  ];
  const filterItems = filters.length > 0 ? filters : defaultFilters;

  const handleSearch = (e) => {
    e.preventDefault();
    onSearch && onSearch({ query, filter: activeFilter });
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-4 mb-6">
      <form onSubmit={handleSearch} className="flex gap-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button type="submit" className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Search
        </button>
      </form>
      <div className="flex gap-2 mt-4">
        {filterItems.map(filter => (
          <button
            key={filter.id}
            onClick={() => setActiveFilter(filter.id)}
            className={"px-4 py-1 rounded-full text-sm " + (activeFilter === filter.id ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200")}
          >
            {filter.label}
          </button>
        ))}
      </div>
    </div>
  );
};
''',
                "keywords": ["search", "header", "filter", "query"],
                "tags": ["search", "header"],
            },
            "progress_bar": {
                "name": "ProgressBar",
                "description": "Progress bar with percentage display",
                "code": '''
const ProgressBar = ({ value = 0, max = 100, label = "", showPercent = true, color = "blue" }) => {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));
  const colors = {
    blue: "bg-blue-600",
    green: "bg-green-600",
    red: "bg-red-600",
    yellow: "bg-yellow-500"
  };

  return (
    <div className="w-full">
      {(label || showPercent) && (
        <div className="flex justify-between mb-2">
          {label && <span className="text-sm font-medium text-gray-700">{label}</span>}
          {showPercent && <span className="text-sm text-gray-500">{percent.toFixed(0)}%</span>}
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className={"h-2.5 rounded-full transition-all " + colors[color]} style={{ width: percent + "%" }}></div>
      </div>
    </div>
  );
};
''',
                "keywords": ["progress", "bar", "percentage", "loading"],
                "tags": ["progress", "bar"],
            },
            "avatar_group": {
                "name": "AvatarGroup",
                "description": "Group of overlapping avatars",
                "code": '''
const AvatarGroup = ({ users, max = 4 }) => {
  const defaultUsers = [
    { name: "John", image: "https://i.pravatar.cc/100?img=1" },
    { name: "Sarah", image: "https://i.pravatar.cc/100?img=2" },
    { name: "Mike", image: "https://i.pravatar.cc/100?img=3" },
    { name: "Emily", image: "https://i.pravatar.cc/100?img=4" },
    { name: "Tom", image: "https://i.pravatar.cc/100?img=5" }
  ];
  const items = users || defaultUsers;
  const visible = items.slice(0, max);
  const remaining = items.length - max;

  return (
    <div className="flex -space-x-3">
      {visible.map((user, i) => (
        <div key={i} className="w-10 h-10 rounded-full border-2 border-white overflow-hidden" title={user.name}>
          <img src={user.image} alt={user.name} className="w-full h-full object-cover" />
        </div>
      ))}
      {remaining > 0 && (
        <div className="w-10 h-10 rounded-full border-2 border-white bg-gray-200 flex items-center justify-center">
          <span className="text-xs font-medium text-gray-600">+{remaining}</span>
        </div>
      )}
    </div>
  );
};
''',
                "keywords": ["avatar", "group", "users", "team"],
                "tags": ["avatar", "group"],
            },
            "badge_status": {
                "name": "BadgeStatus",
                "description": "Status badge with color variants",
                "code": '''
const BadgeStatus = ({ status = "active", label }) => {
  const statusConfig = {
    active: { bg: "bg-green-100", text: "text-green-800", label: "Active" },
    pending: { bg: "bg-yellow-100", text: "text-yellow-800", label: "Pending" },
    inactive: { bg: "bg-gray-100", text: "text-gray-800", label: "Inactive" },
    error: { bg: "bg-red-100", text: "text-red-800", label: "Error" }
  };
  const config = statusConfig[status] || statusConfig.active;

  return (
    <span className={"inline-flex items-center px-3 py-1 rounded-full text-sm font-medium " + config.bg + " " + config.text}>
      <span className={"w-2 h-2 rounded-full mr-2 " + config.text.replace("text-", "bg-")}></span>
      {label || config.label}
    </span>
  );
};
''',
                "keywords": ["badge", "status", "tag", "label"],
                "tags": ["badge", "status"],
            },
        }

        # Create components
        created = []
        for key, comp in COMPONENTS.items():
            parts = key.split("_", 1)
            comp_type = parts[0]
            variant = parts[1] if len(parts) > 1 else "default"
            
            item = LibraryItem.objects.create(
                name=comp["name"],
                slug=key,
                description=comp["description"],
                item_type="component",
                language="jsx",  # PHASE 1: Browser-ready, no transformation needed
                code=comp["code"].strip(),
                keywords=comp["keywords"],
                tags=comp["tags"],
                quality_score=0.9,
                is_active=True,
                is_public=True,
                is_approved=True,  # CRITICAL: Required for library search to find this
                needs_review=False,
                created_by="admin",
            )
            created.append({"id": str(item.id), "name": comp["name"]})
        
        return Response({
            'success': True,
            'cleared': existing_count,
            'created': len(created),
            'components': created
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=500)





