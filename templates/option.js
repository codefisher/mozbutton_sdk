toolbar_buttons.toolbar_button_loader(toolbar_buttons, {
	%s
});
%s
window.addEventListner('load', function() {
	if(window.arguments.length) {
		window.documentElement.showPane(document.getElementById(window.arguments[0]));
	}
}, false);