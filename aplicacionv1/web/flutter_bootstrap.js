{{flutter_js}}
{{flutter_build_config}}
_flutter.loader.load({onEntrypointLoaded: async function(initializer) {
  const appRunner = await initializer.initializeEngine();
  await appRunner.runApp();
  document.getElementById('startup')?.remove();
}});
