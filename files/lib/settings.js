settingWatcher: function(pref, func) {
	this.prefs = toolbar_buttons.interfaces.PrefService.getBranch(pref);
	this.prefs.QueryInterface(Components.interfaces.nsIPrefBranch2);
	this.pref = pref;
	this.func = func;

	this.startup = function() {
		this.prefs.addObserver("", this, false);
		var self = this;
		toolbar_buttons.registerCleanUpFunction(function() {
			self.prefs.removeObserver("", self);
		});
	};

	this.shutdown = function() {
		this.prefs.removeObserver("", this);
	};

	this.observe = function(subject, topic, data) {
		if (topic != "nsPref:changed") {
			return;
		}
		try {
			this.func(subject, topic, data);
		} catch(e) {} // button might not exist
	};
}