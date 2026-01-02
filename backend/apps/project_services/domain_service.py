"""
Domain Management Service
Handle custom domain connection via Vercel/Render APIs.
"""
import os
import requests
import secrets
from typing import Dict, Optional, List, Any
from dataclasses import dataclass


@dataclass
class DNSRecord:
    type: str  # A, CNAME, TXT
    name: str
    value: str
    ttl: int = 3600


@dataclass
class DomainStatus:
    domain: str
    is_verified: bool
    ssl_status: str
    dns_records: List[DNSRecord]
    error: Optional[str] = None


class DomainService:
    """
    Manages custom domain configuration for deployed projects.
    Uses Vercel API for domain management.
    """
    
    VERCEL_API = "https://api.vercel.com"
    
    def __init__(self):
        self.vercel_token = os.environ.get('VERCEL_TOKEN', '')
        self.vercel_team_id = os.environ.get('VERCEL_TEAM_ID', '')
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.vercel_token}',
            'Content-Type': 'application/json'
        }
    
    def add_domain(self, project_id: str, domain: str) -> DomainStatus:
        """
        Add a custom domain to a Vercel project.
        
        Args:
            project_id: Vercel project ID or name
            domain: Domain to add (e.g., "myapp.com")
            
        Returns:
            DomainStatus with verification info
        """
        if not self.vercel_token:
            return self._mock_add_domain(domain)
        
        params = {}
        if self.vercel_team_id:
            params['teamId'] = self.vercel_team_id
        
        # Add domain to project
        response = requests.post(
            f"{self.VERCEL_API}/v10/projects/{project_id}/domains",
            headers=self.headers,
            params=params,
            json={'name': domain}
        )
        
        if response.status_code not in [200, 201]:
            return DomainStatus(
                domain=domain,
                is_verified=False,
                ssl_status='error',
                dns_records=[],
                error=response.json().get('error', {}).get('message', 'Unknown error')
            )
        
        data = response.json()
        
        # Generate DNS records
        dns_records = self._get_dns_records(domain, data)
        
        return DomainStatus(
            domain=domain,
            is_verified=data.get('verified', False),
            ssl_status='pending' if not data.get('verified') else 'active',
            dns_records=dns_records
        )
    
    def _get_dns_records(self, domain: str, vercel_response: Dict) -> List[DNSRecord]:
        """Generate DNS records user needs to configure."""
        records = []
        
        # A record for root domain
        if not domain.startswith('www.'):
            records.append(DNSRecord(
                type='A',
                name='@',
                value='76.76.21.21'  # Vercel's IP
            ))
        
        # CNAME for www
        records.append(DNSRecord(
            type='CNAME',
            name='www',
            value='cname.vercel-dns.com'
        ))
        
        # Verification TXT record if needed
        verification = vercel_response.get('verification', [])
        for v in verification:
            if v.get('type') == 'TXT':
                records.append(DNSRecord(
                    type='TXT',
                    name=v.get('domain', '@').replace(domain, '').strip('.') or '@',
                    value=v.get('value', '')
                ))
        
        return records
    
    def check_domain_status(self, project_id: str, domain: str) -> DomainStatus:
        """Check the current status of a domain."""
        if not self.vercel_token:
            return self._mock_check_domain(domain)
        
        params = {}
        if self.vercel_team_id:
            params['teamId'] = self.vercel_team_id
        
        response = requests.get(
            f"{self.VERCEL_API}/v9/projects/{project_id}/domains/{domain}",
            headers=self.headers,
            params=params
        )
        
        if response.status_code != 200:
            return DomainStatus(
                domain=domain,
                is_verified=False,
                ssl_status='error',
                dns_records=[],
                error='Domain not found'
            )
        
        data = response.json()
        
        return DomainStatus(
            domain=domain,
            is_verified=data.get('verified', False),
            ssl_status='active' if data.get('verified') else 'pending',
            dns_records=self._get_dns_records(domain, data)
        )
    
    def remove_domain(self, project_id: str, domain: str) -> bool:
        """Remove a custom domain from a project."""
        if not self.vercel_token:
            return True
        
        params = {}
        if self.vercel_team_id:
            params['teamId'] = self.vercel_team_id
        
        response = requests.delete(
            f"{self.VERCEL_API}/v9/projects/{project_id}/domains/{domain}",
            headers=self.headers,
            params=params
        )
        
        return response.status_code in [200, 204]
    
    def _mock_add_domain(self, domain: str) -> DomainStatus:
        """Mock domain addition for development."""
        verification_token = secrets.token_hex(16)
        
        return DomainStatus(
            domain=domain,
            is_verified=False,
            ssl_status='pending',
            dns_records=[
                DNSRecord(type='A', name='@', value='76.76.21.21'),
                DNSRecord(type='CNAME', name='www', value='cname.vercel-dns.com'),
                DNSRecord(type='TXT', name='_vercel', value=f'vc-domain-verify={verification_token}'),
            ]
        )
    
    def _mock_check_domain(self, domain: str) -> DomainStatus:
        """Mock domain check for development."""
        return DomainStatus(
            domain=domain,
            is_verified=True,
            ssl_status='active',
            dns_records=[]
        )
    
    def generate_domain_instructions(self, status: DomainStatus) -> str:
        """Generate user-friendly instructions for DNS setup."""
        if status.is_verified:
            return f"Your domain {status.domain} is verified and active!"
        
        instructions = f"""
## Configure DNS for {status.domain}

Add the following DNS records at your domain registrar:

| Type | Name | Value | TTL |
|------|------|-------|-----|
"""
        for record in status.dns_records:
            instructions += f"| {record.type} | {record.name} | {record.value} | {record.ttl} |\n"
        
        instructions += """

### Steps:
1. Log in to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)
2. Find the DNS settings or DNS management section
3. Add each record from the table above
4. Wait 5-10 minutes for propagation
5. Click "Verify" to confirm your domain is connected

Note: DNS changes can take up to 48 hours to fully propagate.
"""
        return instructions


# Singleton
domain_service = DomainService()


