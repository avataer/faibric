"""
Visual Editing Script - Injected into deployed apps for click-to-edit functionality.

This script enables:
1. Element hover highlighting
2. Click detection with element info
3. Applying edits from the parent frame
"""

VISUAL_EDIT_SCRIPT = '''
<script>
(function() {
  // Only run in iframe context
  if (window === window.parent) return;

  let isEditModeEnabled = false;
  let highlightedElement = null;
  let highlightOverlay = null;

  // Create highlight overlay element
  function createHighlightOverlay() {
    if (highlightOverlay) return;
    highlightOverlay = document.createElement('div');
    highlightOverlay.id = 'faibric-highlight-overlay';
    highlightOverlay.style.cssText = `
      position: fixed;
      pointer-events: none;
      border: 2px solid #2563eb;
      background: rgba(37, 99, 235, 0.1);
      z-index: 999999;
      transition: all 0.1s ease;
      display: none;
    `;
    document.body.appendChild(highlightOverlay);
  }

  // Get unique selector for element
  function getSelector(element) {
    if (element.id) {
      return '#' + element.id;
    }

    let path = [];
    while (element && element.nodeType === Node.ELEMENT_NODE) {
      let selector = element.nodeName.toLowerCase();
      if (element.className && typeof element.className === 'string') {
        const classes = element.className.trim().split(/\\s+/).slice(0, 2);
        if (classes.length > 0 && classes[0]) {
          selector += '.' + classes.join('.');
        }
      }

      // Add nth-child if needed for uniqueness
      let sibling = element;
      let nth = 1;
      while (sibling.previousElementSibling) {
        sibling = sibling.previousElementSibling;
        if (sibling.nodeName === element.nodeName) nth++;
      }
      if (nth > 1) selector += ':nth-of-type(' + nth + ')';

      path.unshift(selector);
      element = element.parentNode;

      // Stop at body
      if (element === document.body) break;
    }

    return path.join(' > ');
  }

  // Get element type
  function getElementType(element) {
    const tag = element.tagName.toLowerCase();

    if (tag === 'button' || element.getAttribute('role') === 'button' ||
        element.className.includes('btn') || element.className.includes('button')) {
      return 'button';
    }
    if (tag === 'img') return 'image';
    if (tag === 'a') return 'link';
    if (tag === 'input' || tag === 'textarea') return 'input';
    if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div'].includes(tag)) {
      // Check if it's primarily text content
      const textLength = (element.textContent || '').trim().length;
      const childElements = element.children.length;
      if (textLength > 0 && childElements < 3) return 'text';
    }

    return 'element';
  }

  // Get current value based on element type
  function getCurrentValue(element, elementType) {
    switch (elementType) {
      case 'text':
      case 'button':
      case 'link':
        return element.textContent || '';
      case 'image':
        return element.src || element.getAttribute('src') || '';
      case 'input':
        return element.value || element.placeholder || '';
      default:
        return element.textContent || '';
    }
  }

  // Update highlight position
  function updateHighlight(element) {
    if (!highlightOverlay || !element) {
      if (highlightOverlay) highlightOverlay.style.display = 'none';
      return;
    }

    const rect = element.getBoundingClientRect();
    highlightOverlay.style.display = 'block';
    highlightOverlay.style.top = rect.top + 'px';
    highlightOverlay.style.left = rect.left + 'px';
    highlightOverlay.style.width = rect.width + 'px';
    highlightOverlay.style.height = rect.height + 'px';
  }

  // Handle mouse move for hover highlighting
  function handleMouseMove(e) {
    if (!isEditModeEnabled) return;

    const element = e.target;
    if (element === highlightOverlay) return;

    // Skip certain elements
    if (element.id === 'faibric-highlight-overlay' ||
        element.tagName === 'HTML' ||
        element.tagName === 'BODY') {
      updateHighlight(null);
      return;
    }

    highlightedElement = element;
    updateHighlight(element);

    // Notify parent
    window.parent.postMessage({
      type: 'element_hover',
      selector: getSelector(element)
    }, '*');
  }

  // Handle click for element selection
  function handleClick(e) {
    if (!isEditModeEnabled) return;

    e.preventDefault();
    e.stopPropagation();

    const element = e.target;
    if (element.id === 'faibric-highlight-overlay') return;

    const selector = getSelector(element);
    const elementType = getElementType(element);
    const currentValue = getCurrentValue(element, elementType);

    window.parent.postMessage({
      type: 'element_click',
      selector: selector,
      elementType: elementType,
      currentValue: currentValue
    }, '*');
  }

  // Handle messages from parent
  window.addEventListener('message', function(event) {
    const data = event.data;
    if (!data || !data.type) return;

    switch (data.type) {
      case 'enable_visual_editing':
        isEditModeEnabled = true;
        createHighlightOverlay();
        document.body.style.cursor = 'crosshair';
        break;

      case 'disable_visual_editing':
        isEditModeEnabled = false;
        if (highlightOverlay) highlightOverlay.style.display = 'none';
        document.body.style.cursor = '';
        break;

      case 'highlight_element':
        if (data.selector) {
          try {
            const element = document.querySelector(data.selector);
            if (element) updateHighlight(element);
          } catch (e) {}
        }
        break;

      case 'clear_highlight':
        updateHighlight(null);
        break;

      case 'apply_edit':
        try {
          const element = document.querySelector(data.selector);
          if (!element) return;

          if (data.elementType === 'text' || data.elementType === 'button' || data.elementType === 'link') {
            element.textContent = data.newValue;
          } else if (data.elementType === 'image') {
            element.src = data.newValue;
          } else if (data.elementType === 'style') {
            const styles = JSON.parse(data.newValue);
            Object.assign(element.style, styles);
          }
        } catch (e) {
          console.error('Faibric: Failed to apply edit', e);
        }
        break;
    }
  });

  // Add event listeners
  document.addEventListener('mousemove', handleMouseMove, true);
  document.addEventListener('click', handleClick, true);

  // Notify parent that iframe is ready
  window.parent.postMessage({ type: 'iframe_ready' }, '*');

  console.log('Faibric Visual Editing: Ready');
})();
</script>
'''


def get_visual_edit_script():
    """Return the visual editing script to inject into deployed apps."""
    return VISUAL_EDIT_SCRIPT
