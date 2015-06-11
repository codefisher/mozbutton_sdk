setUpMenuShower: function(doc) {
	var observer = {
		observe: function(aSubject, aTopic, aData) {
			var menu = doc.getElementById(aData);
			if(menu) {
				menu.setAttribute('hidden', !this.prefs.getBoolPref(aData));
			}
		},
		unregister: function() {
			this.prefs.removeObserver("", this);
		},
		register: function() {
			this.prefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService).getBranch("{{pref_root}}showamenu.");
			this.prefs.addObserver("", this, false);
			var self = this;
			toolbar_buttons.registerCleanUpFunction(function() {
				self.prefs.removeObserver("", self);
			});
			var attrList = this.prefs.getChildList('', {});
			for(var i in attrList) {
				var menu = doc.getElementById(attrList[i]);
				if(menu) {
					menu.setAttribute('hidden', !this.prefs.getBoolPref(attrList[i]));
				}
			}
		}
	};
	observer.register();
}

sortMenu: function(event, aMenu) {
	if(aMenu.sorted || !aMenu.getAttribute('sortable')){
		return;
	}
	var menuitems = [];
	while(aMenu.firstChild) {
		menuitems.push(aMenu.firstChild);
		aMenu.removeChild(aMenu.firstChild);
	}
	menuitems.sort(function(a, b) { return a.getAttribute('label').toLowerCase() > b.getAttribute('label').toLowerCase(); });
	for(var i in menuitems) {
		aMenu.appendChild(menuitems[i]);
	}
	aMenu.sorted = true;
}

menuLoaderEvent: function(event) {
	var win = event.target.ownerDocument.defaultView;
	var menuitem = event.originalTarget;
	if(menuitem.getAttribute('showamenu')) {
		// so this is one of those menu items that as a fake submenu, show it
		var cEvent = new Event('command', {
		    'view': win,
		    'bubbles': false,
		    'cancelable': true,
		    'target': menuitem,
		});
		menuitem.dispatchEvent(cEvent);
	}
}

handelMenuLoaders: function(event, item) {
	if(item._handelMenuLoaders)
		return;
	item.addEventListener('DOMMenuItemActive', toolbar_buttons.menuLoaderEvent, false);
	item._handelMenuLoaders = true;
}