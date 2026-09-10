# AFP4 deployment records

This directory versions the deployed web configuration and source-to-server
verification evidence. The server hosts static build artifacts, not Git
checkouts; its directories do not have a running branch.

## Sources of truth

| Site | Application source | Server directory |
| --- | --- | --- |
| Private GIS | `NuGlobalSolutionsLLC/AFP4_Private`, `main` | `/var/www/html/apps/AFP4` |
| Public GIS | `NuGlobalSolutionsLLC/AFP04_Public`, `main` | `/var/www/html/apps/AFP04` |
| Storymap | `NuGlobalSolutionsLLC/AFP04-storymap`, `main` | `/var/www/html/apps/storymap/afp4` |

Build each application from its approved source and lockfile with `npm ci` and
`npm run build`. Deploy the resulting `dist/spa/`, not the historical generated
`dist/` files still tracked in those repositories. The repositories already
ignore new `dist/` output; removal of historical tracked builds is separate
cleanup, not part of this release.

Transect source copies in each application's `public/` are tracked. Their
builder, original diagram provenance, tests, and source archive hashes are in
`transects/`. The original supplied ZIPs remain external inputs; they are not
uploaded to Git. Generated releases are verified against the exact source
archives before publication.

## Web configuration

`nginx/apps_nuglobalsolutions.conf` is the byte-for-byte active configuration
snapshot from `/etc/nginx/sites-enabled/apps_nuglobalsolutions`, verified on
September 10, 2026. It includes the existing Private shell/data, Public shell,
and all 36 transect HTML revalidation rules, including 304 responses. Certificate
and private-key files are **not** included; the configuration only refers to
their server paths.

This snapshot is not an automatic deployment mechanism or a claim that unrelated
legacy TLS/PHP settings have been modernized. Before changing nginx, compare the
live configuration, preserve a backup outside the web root, review a scoped diff,
run `nginx -t`, and reload only after validation. Do not overwrite later server
changes by blindly copying this snapshot.

## Release verification and retention

See `releases/2026-09-10-main-sync.md` and its full SHA-256 manifest. A successful
sync means every file in the approved fresh build has the same hash at the live
path. Extra legacy hashed assets may intentionally remain for cached browsers;
they must not be deleted by a mirror/delete operation.

Release records and rollback directories identify what changed and how to
recover it. Do not infer client GIS signoff from publication, banner removal,
or merging the source that already reproduces production.
