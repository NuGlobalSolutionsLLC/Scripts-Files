"""Copy only verified generated transect artifacts into an application's public/.

This is a local build-output installation, not a deployment. Refuses existing
uncommitted target changes; unrelated files and old hashed assets are retained.
"""
import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--application', type=pathlib.Path, required=True)
    args = parser.parse_args()
    build, app = args.build.resolve(), args.application.resolve()
    public = app / 'public'
    assert public.is_dir() and public.resolve() == public
    manifest = json.loads((build / 'manifest.json').read_text())
    files = {n: digest for n, digest in manifest.items()
             if re.fullmatch(r's2(aa|bb|cc|dd|ee|ff)_(mr|max)\.html', n)
             or re.fullmatch(r'transects-assets/[A-Za-z0-9.-]+\.(js|json|css|png)', n)}
    assert len(files) == 27
    for name, digest in files.items():
        assert hashlib.sha256((build / name).read_bytes()).hexdigest() == digest
        assert not (public / name).is_symlink()
    changes = subprocess.check_output(
        ['git', '-C', str(app), 'status', '--porcelain', '--',
         *['public/' + name for name in files]], text=True)
    assert not changes, 'Uncommitted target changes exist; inspect before replacing'
    for name in files:
        target = public / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(build / name, target)
    for name, digest in files.items():
        assert hashlib.sha256((public / name).read_bytes()).hexdigest() == digest
    print(json.dumps({'application': str(app), 'installedFiles': len(files)}))


if __name__ == '__main__':
    main()
