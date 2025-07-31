from django.http import Http404, FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_control
import os
import mimetypes

@require_GET
@cache_control(max_age=3600)  # Cache for 1 hour
def serve_media(request, path):
    """
    Serve media files in production
    """
    # Security check - ensure path is within MEDIA_ROOT
    if '..' in path or path.startswith('/'):
        raise Http404("Invalid path")
    
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")
    
    # Check if path is within MEDIA_ROOT (security)
    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.MEDIA_ROOT)):
        raise Http404("Access denied")
    
    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    # Return file response
    try:
        return FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=False
        )
    except IOError:
        raise Http404("File not found")
