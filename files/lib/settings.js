settingWatcher: function(pref, func) {
	this.prefs = toolbar_buttons.interfaces.PrefService.getBranch(pref);
	this.prefs.QueryInterface(Components.interfaces.nsIPrefBranch2);

	var observer = {
		observe: function(subject, topic, data) {
			if (topic != "nsPref:changed") {
				return;
			}
			try {
				func(subject, topic, data);
			} catch(e) {} // button might not exist
		}
	};

	this.startup = function() {
		this.prefs.addObserver("", observer, false);
		toolbar_buttons.registerCleanUpFunction(function() {
			self.prefs.removeObserver("", observer);
		});
	};

	this.shutdown = function() {
		this.prefs.removeObserver("", observer);
	};
}