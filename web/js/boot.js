// Runs before the page paints. It marks the page as JavaScript-enabled, so the hidden-until-revealed
// starting states in polish.css only apply when the animation code is actually going to run.
document.documentElement.classList.add("js");
