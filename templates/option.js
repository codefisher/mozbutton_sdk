toolbar_buttons.toolbar_button_loader(toolbar_buttons, {
	%s
});
%s

window.addEventListener('load', function() {
	if(window.arguments && window.arguments.length) {
		window.document.documentElement.showPane(document.getElementById(window.arguments[0]));
	}
}, false);