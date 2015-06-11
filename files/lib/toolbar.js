toggleToolbar: function(aEvent, toolbar_id) {
	var doc = aEvent.target.ownerDocument;
	var win = doc.defaultView;
	if(!aEvent || !aEvent.originalTarget || toolbar_id != aEvent.originalTarget.parentNode.id) {
		var toolbar = doc.getElementById(toolbar_id);
		try {
			CustomizableUI.setToolbarVisibility(toolbar_id, (toolbar.collapsed || toolbar.hidden));
		} catch (e) {
			if (toolbar.collapsed || toolbar.hidden) {
				if (toolbar.hasAttribute('hidden')) {
					toolbar.setAttribute('hidden', 'false');
					toolbar.setAttribute('collapsed', 'false');
				} else {
					toolbar.setAttribute('collapsed', 'false');
				}
			} else {
				if (toolbar.hasAttribute('hidden')) {
					toolbar.setAttribute('hidden', 'true');
				} else {
					toolbar.setAttribute('collapsed', 'true');
				}
			}
		}
	}
}