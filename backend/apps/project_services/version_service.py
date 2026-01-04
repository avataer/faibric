"""
Version Control Service
Track project versions and enable rollback.
"""
import difflib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class VersionDiff:
    added_lines: int
    removed_lines: int
    diff_html: str


@dataclass
class Version:
    version_number: int
    created_at: datetime
    change_description: str
    is_deployed: bool
    code_preview: str  # First 500 chars


class VersionService:
    """
    Manages version history and rollback for projects.
    """
    
    def create_version(
        self,
        project_id: str,
        code: str,
        config: Dict,
        description: str = '',
        commit_hash: str = ''
    ) -> Dict[str, Any]:
        """
        Create a new version snapshot.
        Returns version info.
        """
        from apps.project_services.models import ProjectVersion
        from apps.projects.models import Project
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return {'error': 'Project not found'}
        
        # Get next version number
        last_version = ProjectVersion.objects.filter(project=project).order_by('-version_number').first()
        next_version = (last_version.version_number + 1) if last_version else 1
        
        # Create version
        version = ProjectVersion.objects.create(
            project=project,
            version_number=next_version,
            commit_hash=commit_hash,
            code_snapshot=code,
            config_snapshot=config,
            change_description=description or f'Version {next_version}'
        )
        
        return {
            'version_number': version.version_number,
            'id': str(version.id),
            'created_at': version.created_at.isoformat()
        }
    
    def get_versions(self, project_id: str, limit: int = 20) -> List[Version]:
        """
        Get version history for a project.
        """
        from apps.project_services.models import ProjectVersion
        
        versions = ProjectVersion.objects.filter(
            project_id=project_id
        ).order_by('-version_number')[:limit]
        
        return [
            Version(
                version_number=v.version_number,
                created_at=v.created_at,
                change_description=v.change_description,
                is_deployed=v.is_deployed,
                code_preview=v.code_snapshot[:500] + '...' if len(v.code_snapshot) > 500 else v.code_snapshot
            )
            for v in versions
        ]
    
    def get_diff(self, project_id: str, version_a: int, version_b: int) -> VersionDiff:
        """
        Get diff between two versions.
        """
        from apps.project_services.models import ProjectVersion
        
        try:
            va = ProjectVersion.objects.get(project_id=project_id, version_number=version_a)
            vb = ProjectVersion.objects.get(project_id=project_id, version_number=version_b)
        except ProjectVersion.DoesNotExist:
            return VersionDiff(added_lines=0, removed_lines=0, diff_html='<p>Version not found</p>')
        
        # Generate diff
        diff = difflib.unified_diff(
            va.code_snapshot.splitlines(keepends=True),
            vb.code_snapshot.splitlines(keepends=True),
            fromfile=f'v{version_a}',
            tofile=f'v{version_b}'
        )
        
        diff_lines = list(diff)
        added = len([l for l in diff_lines if l.startswith('+')])
        removed = len([l for l in diff_lines if l.startswith('-')])
        
        # Generate HTML
        diff_html = self._diff_to_html(diff_lines)
        
        return VersionDiff(
            added_lines=added,
            removed_lines=removed,
            diff_html=diff_html
        )
    
    def _diff_to_html(self, diff_lines: List[str]) -> str:
        """Convert diff to HTML with syntax highlighting."""
        html = '<pre class="diff-view">'
        
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                html += f'<span class="diff-added">{self._escape(line)}</span>'
            elif line.startswith('-') and not line.startswith('---'):
                html += f'<span class="diff-removed">{self._escape(line)}</span>'
            elif line.startswith('@@'):
                html += f'<span class="diff-hunk">{self._escape(line)}</span>'
            else:
                html += self._escape(line)
        
        html += '</pre>'
        return html
    
    def _escape(self, text: str) -> str:
        """Escape HTML characters."""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    def rollback(self, project_id: str, version_number: int) -> Dict[str, Any]:
        """
        Rollback project to a specific version.
        Creates a new version with the old code.
        """
        from apps.project_services.models import ProjectVersion
        from apps.projects.models import Project
        
        try:
            version = ProjectVersion.objects.get(project_id=project_id, version_number=version_number)
            project = Project.objects.get(id=project_id)
        except (ProjectVersion.DoesNotExist, Project.DoesNotExist):
            return {'error': 'Version or project not found'}
        
        # Create new version with old code
        new_version = self.create_version(
            project_id=project_id,
            code=version.code_snapshot,
            config=version.config_snapshot,
            description=f'Rollback to v{version_number}'
        )
        
        # Update project's current code
        project.generated_code = version.code_snapshot
        project.save(update_fields=['generated_code'])
        
        return {
            'success': True,
            'new_version': new_version,
            'rolled_back_to': version_number
        }
    
    def generate_version_ui_code(self) -> str:
        """
        Generate React code for version management UI.
        """
        return '''
// Version History Component
const VersionHistory = ({ projectId, onRollback }) => {
  const [versions, setVersions] = React.useState([]);
  const [selectedVersion, setSelectedVersion] = React.useState(null);
  const [diff, setDiff] = React.useState(null);
  const [loading, setLoading] = React.useState(true);
  
  React.useEffect(() => {
    fetchVersions();
  }, [projectId]);
  
  const fetchVersions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/projects/${projectId}/versions`);
      const data = await response.json();
      setVersions(data.versions || []);
    } catch (err) {
      console.error("Failed to fetch versions:", err);
    }
    setLoading(false);
  };
  
  const viewDiff = async (versionNumber) => {
    const currentVersion = versions[0]?.version_number;
    if (!currentVersion) return;
    
    try {
      const response = await fetch(
        `/api/projects/${projectId}/diff?from=${versionNumber}&to=${currentVersion}`
      );
      const data = await response.json();
      setDiff(data);
      setSelectedVersion(versionNumber);
    } catch (err) {
      console.error("Failed to fetch diff:", err);
    }
  };
  
  const handleRollback = async (versionNumber) => {
    if (!confirm(`Are you sure you want to rollback to version ${versionNumber}?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/projects/${projectId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: versionNumber })
      });
      
      if (response.ok) {
        alert("Rollback successful!");
        fetchVersions();
        if (onRollback) onRollback();
      }
    } catch (err) {
      console.error("Rollback failed:", err);
      alert("Rollback failed. Please try again.");
    }
  };
  
  if (loading) {
    return <div className="animate-pulse p-4">Loading versions...</div>;
  }
  
  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">Version History</h2>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Version List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h3 className="font-semibold">All Versions</h3>
          </div>
          <ul className="divide-y max-h-96 overflow-y-auto">
            {versions.map((version) => (
              <li 
                key={version.version_number}
                className={`p-4 hover:bg-gray-50 cursor-pointer ${
                  selectedVersion === version.version_number ? "bg-indigo-50" : ""
                }`}
                onClick={() => viewDiff(version.version_number)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-mono font-bold">v{version.version_number}</span>
                    {version.is_deployed && (
                      <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                        Live
                      </span>
                    )}
                    <p className="text-sm text-gray-600 mt-1">{version.change_description}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(version.created_at).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRollback(version.version_number); }}
                    className="text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    Restore
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
        
        {/* Diff View */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h3 className="font-semibold">
              {selectedVersion ? `Changes in v${selectedVersion}` : "Select a version"}
            </h3>
          </div>
          <div className="p-4 max-h-96 overflow-auto">
            {diff ? (
              <div>
                <div className="flex gap-4 text-sm mb-4">
                  <span className="text-green-600">+{diff.added_lines} added</span>
                  <span className="text-red-600">-{diff.removed_lines} removed</span>
                </div>
                <div 
                  className="font-mono text-sm"
                  dangerouslySetInnerHTML={{ __html: diff.diff_html }}
                />
              </div>
            ) : (
              <p className="text-gray-400">Click a version to see changes</p>
            )}
          </div>
        </div>
      </div>
      
      <style>{`
        .diff-added { background: #dcfce7; display: block; }
        .diff-removed { background: #fee2e2; display: block; }
        .diff-hunk { color: #6366f1; display: block; }
      `}</style>
    </div>
  );
};
'''


# Singleton
version_service = VersionService()



