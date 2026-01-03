from django.apps import AppConfig


class DeploymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.deployment'
    
    def ready(self):
        """Run environment validation at Django startup."""
        # Import triggers the validation
        from . import env_validator
        
        # Log deployment status
        import logging
        logger = logging.getLogger(__name__)
        status = env_validator.get_deployment_status()
        
        if status['vercel']['configured']:
            logger.info("[DEPLOY] Hybrid mode: Vercel + Render")
        else:
            logger.warning("[DEPLOY] Render-only mode (VERCEL_TOKEN not set)")

