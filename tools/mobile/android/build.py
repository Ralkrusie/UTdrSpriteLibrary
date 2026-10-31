"""Build an offline test APK with fixed official Android SDK tools (Windows).

No Gradle, npm, third-party Android runtime or network service is required.
Download the two named archives from dl.google.com/android/repository into
vendor/android before building. The generated test signing key stays in vendor.
"""
import argparse
import hashlib
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--jdk', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    vendor = ROOT / 'vendor/android'
    for name, sha, folder in [('platform-35_r02.zip', '0bb560a90a7a2cbd0dd8348224d518b638fe7949', 'platform'),
                              ('build-tools_r35_windows.zip', 'af059bb67cf7786f45ee0db85e2d24985df1b4b6', 'tools')]:
        archive = vendor / name
        if hashlib.sha1(archive.read_bytes()).hexdigest() != sha:
            raise ValueError('Official SDK checksum mismatch: ' + name)
        destination = out / folder
        with zipfile.ZipFile(archive) as z:
            z.extractall(destination)
    platform = next((out / 'platform').glob('*/android.jar'))
    tools = next((out / 'tools').glob('*/aapt.exe')).parent
    java = args.jdk.resolve() / 'bin'
    env = os.environ.copy()
    env['JAVA_HOME'] = str(args.jdk.resolve())
    env['PATH'] = str(java) + os.pathsep + env['PATH']
    def run(*command):
        subprocess.run([str(x) for x in command], check=True, env=env)
    run(sys.executable, ROOT / 'tools/mobile/build.py', '--out', out / 'assets/web')
    notices = out / 'assets/notices'
    notices.mkdir()
    for name in ('LICENSE', 'ASSET_NOTICE.md', 'THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT / name, notices / name)
    # App-specific entry has no install link or network-dependent service worker.
    page = out / 'assets/web/index.html'
    html = re.sub(r'<footer>.*?</footer>', '', page.read_text(encoding='utf-8'), flags=re.DOTALL)
    page.write_text(html, encoding='utf-8')
    res = out / 'res/drawable'
    res.mkdir(parents=True)
    shutil.copy2(ROOT / 'tools/mobile/icon-192.png', res / 'icon.png')
    run(tools / 'aapt.exe', 'package', '-f', '-M', HERE / 'AndroidManifest.xml', '-S', out / 'res', '-A', out / 'assets', '-I', platform, '-F', out / 'unsigned.apk')
    classes = out / 'classes'
    classes.mkdir()
    run(java / 'javac.exe', '-encoding', 'UTF-8', '--release', '8', '-classpath', platform, '-d', classes, *HERE.glob('src/**/*.java'))
    dex = out / 'dex'
    dex.mkdir()
    run(java / 'java.exe', '-cp', tools / 'lib/d8.jar', 'com.android.tools.r8.D8', '--lib', platform, '--min-api', '28', '--output', dex, *classes.rglob('*.class'))
    with zipfile.ZipFile(out / 'unsigned.apk', 'a', compression=zipfile.ZIP_DEFLATED) as z:
        z.write(dex / 'classes.dex', 'classes.dex')
    run(tools / 'zipalign.exe', '-f', '4', out / 'unsigned.apk', out / 'aligned.apk')
    key = vendor / 'offline-test.jks'
    if not key.exists():
        run(java / 'keytool.exe', '-genkeypair', '-keystore', key, '-storepass', 'android', '-keypass', 'android', '-alias', 'offline-test', '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000', '-dname', 'CN=UTdrSpriteLibrary Local Test')
    apk = out / 'UTdrSpriteLibrary-0.3.0-android.apk'
    signer = tools / 'lib/apksigner.jar'
    run(java / 'java.exe', '-jar', signer, 'sign', '--ks', key, '--ks-pass', 'pass:android', '--ks-key-alias', 'offline-test', '--out', apk, out / 'aligned.apk')
    run(java / 'java.exe', '-jar', signer, 'verify', '--verbose', apk)
    run(tools / 'aapt.exe', 'dump', 'badging', apk)
    print(f'APK: {apk} ({apk.stat().st_size:,} bytes)')

if __name__ == '__main__':
    main()
