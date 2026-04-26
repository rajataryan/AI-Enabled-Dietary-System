const manifest = (() => {
function __memo(fn) {
	let value;
	return () => value ??= (value = fn());
}

return {
	appDir: "_app",
	appPath: "_app",
	assets: new Set([]),
	mimeTypes: {},
	_: {
		client: {start:"_app/immutable/entry/start.DDYsV7_k.js",app:"_app/immutable/entry/app.HD2Sj6Yx.js",imports:["_app/immutable/entry/start.DDYsV7_k.js","_app/immutable/chunks/Dq35mnba.js","_app/immutable/chunks/D3buMfpK.js","_app/immutable/chunks/CZnF69o5.js","_app/immutable/entry/app.HD2Sj6Yx.js","_app/immutable/chunks/xkZYzo2Y.js","_app/immutable/chunks/D3buMfpK.js","_app/immutable/chunks/CZnF69o5.js","_app/immutable/chunks/cfHPKXzL.js","_app/immutable/chunks/BAPVpL6D.js"],stylesheets:[],fonts:[],uses_env_dynamic_public:false},
		nodes: [
			__memo(() => import('./chunks/0-B7X3KtK8.js')),
			__memo(() => import('./chunks/1-BdgBEQRE.js')),
			__memo(() => import('./chunks/2-EyCg4N-O.js').then(function (n) { return n.c; }))
		],
		remotes: {
			
		},
		routes: [
			{
				id: "/[...catchall]",
				pattern: /^(?:\/([^]*))?\/?$/,
				params: [{"name":"catchall","optional":false,"rest":true,"chained":true}],
				page: { layouts: [0,], errors: [1,], leaf: 2 },
				endpoint: null
			}
		],
		prerendered_routes: new Set([]),
		matchers: async () => {
			
			return {  };
		},
		server_assets: {}
	}
}
})();

const prerendered = new Set([]);

const base = "";

export { base, manifest, prerendered };
//# sourceMappingURL=manifest.js.map
