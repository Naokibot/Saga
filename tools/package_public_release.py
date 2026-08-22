from __future__ import annotations
from pathlib import Path
import hashlib, os, shutil, zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=Path('/mnt/data')
VERSION='0.50.0'
STAMP=(2026,8,18,0,0,0)

def add(z,arc,data,mode=0o644):
    i=zipfile.ZipInfo(str(arc).replace(os.sep,'/'),STAMP);i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=(mode&0xffff)<<16;z.writestr(i,data,compresslevel=9)

def clean_source_files():
    excluded={'.git','.venv','__pycache__','build','dist','.pytest_cache','saga_language.egg-info'}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(ROOT)
        if any(x in excluded for x in rel.parts) or p.suffix in {'.pyc','.pyo'}: continue
        if rel.parts[:2]==('implementations','go') and 'bin' in rel.parts: continue
        if rel.parts[:1]==('installer-native',) and ('bin' in rel.parts or 'payload' in rel.parts): continue
        yield p,rel

def make_source_zip():
    out=OUT/f'saga-lang-{VERSION}.zip'
    with zipfile.ZipFile(out,'w') as z:
        for p,rel in clean_source_files():
            mode=0o755 if os.access(p,os.X_OK) and p.suffix not in {'.md','.json','.py'} else 0o644
            add(z,Path(f'saga-lang-{VERSION}')/rel,p.read_bytes(),mode)
    return out

def copy_binaries():
    result=[]
    mapping={
      ROOT/f'installer-native/bin/saga-installer-linux-amd64-{VERSION}': OUT/f'saga-installer-linux-amd64-{VERSION}.run',
      ROOT/f'installer-native/bin/saga-installer-linux-arm64-{VERSION}': OUT/f'saga-installer-linux-arm64-{VERSION}.run',
      ROOT/f'installer-native/bin/saga-installer-windows-amd64-{VERSION}.exe': OUT/f'saga-installer-windows-amd64-{VERSION}.exe',
      ROOT/f'installer-native/bin/saga-installer-windows-arm64-{VERSION}.exe': OUT/f'saga-installer-windows-arm64-{VERSION}.exe',
      ROOT/'implementations/go/bin/saga-native-linux-amd64': OUT/f'saga-native-linux-amd64-{VERSION}',
      ROOT/'implementations/go/bin/saga-native-linux-arm64': OUT/f'saga-native-linux-arm64-{VERSION}',
      ROOT/'implementations/go/bin/saga-native-windows-amd64.exe': OUT/f'saga-native-windows-amd64-{VERSION}.exe',
      ROOT/'implementations/go/bin/saga-native-windows-arm64.exe': OUT/f'saga-native-windows-arm64-{VERSION}.exe',
      ROOT/'implementations/go/bin/saga-native-darwin-amd64': OUT/f'saga-native-macos-amd64-{VERSION}',
      ROOT/'implementations/go/bin/saga-native-darwin-arm64': OUT/f'saga-native-macos-arm64-{VERSION}',
    }
    for a,b in mapping.items():
        if not a.is_file(): raise SystemExit(f'missing {a}')
        shutil.copy2(a,b); result.append(b)
    return result

def installers_zip(binaries):
    installers=[p for p in binaries if 'installer-' in p.name]
    out=OUT/f'saga-installers-{VERSION}.zip'
    readme=f'''Saga Native {VERSION} offline installers\n\nNo Python, Go, Java, Node, .NET, clang or GCC runtime/toolchain is required.\nThe installer embeds one statically compiled Saga Native runtime for the target platform and runs native conformance after installation.\n\nLinux x86-64:\n  chmod +x saga-installer-linux-amd64-{VERSION}.run\n  ./saga-installer-linux-amd64-{VERSION}.run\n\nWindows x86-64:\n  .\\saga-installer-windows-amd64-{VERSION}.exe\n'''.encode()
    with zipfile.ZipFile(out,'w') as z:
        add(z,Path(f'saga-installers-{VERSION}/README.txt'),readme)
        for p in installers:add(z,Path(f'saga-installers-{VERSION}')/p.name,p.read_bytes(),0o755)
    return out

def native_sdk_zip(binaries):
    runtimes=[p for p in binaries if 'saga-native-' in p.name and 'installer' not in p.name]
    out=OUT/f'saga-native-sdk-{VERSION}.zip'
    with zipfile.ZipFile(out,'w') as z:
        add(z,Path(f'saga-native-sdk-{VERSION}/README.md'),(ROOT/'docs/NATIVE_INDEPENDENCE_0.12.md').read_bytes())
        for doc in ['docs/BOOTSTRAP_TRUST_0.12.md','spec/SAGA_NATIVE_DISTRIBUTION_PROFILE_1.0_FINAL_CANDIDATE.md','spec/SAGA_SELF_HOSTING_PROFILE_1.0_FINAL_CANDIDATE.md','SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md','spec/saga-1.0.ebnf']:
            p=ROOT/doc;add(z,Path(f'saga-native-sdk-{VERSION}')/doc,p.read_bytes())
        for p in runtimes:add(z,Path(f'saga-native-sdk-{VERSION}/bin')/p.name,p.read_bytes(),0o755)
    return out

def standards_zip():
    out=OUT/f'saga-language-specification-{VERSION}.zip'
    paths=[ROOT/'SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md',ROOT/'spec/saga-1.0.ebnf',ROOT/'spec/SAGA_NATIVE_DISTRIBUTION_PROFILE_1.0_FINAL_CANDIDATE.md',ROOT/'spec/SAGA_SELF_HOSTING_PROFILE_1.0_FINAL_CANDIDATE.md',ROOT/'docs/NATIVE_INDEPENDENCE_0.12.md',ROOT/'docs/BOOTSTRAP_TRUST_0.12.md',ROOT/f'SAGA_REVIEW_HANDOFF_{VERSION}.md',ROOT/f'SAGA_PLATFORM_QUALIFICATION_{VERSION}.md',ROOT/f'saga-REVIEW_REPORT-{VERSION}.md',ROOT/f'saga-VALIDATION-{VERSION}.md',ROOT/f'release/source-manifest-{VERSION}.json',ROOT/f'validation/production-ga-{VERSION}.json']
    with zipfile.ZipFile(out,'w') as z:
        for p in paths:add(z,Path(f'saga-language-specification-{VERSION}')/p.relative_to(ROOT),p.read_bytes())
    return out

def main():
    bins=copy_binaries(); src=make_source_zip(); iz=installers_zip(bins); sdk=native_sdk_zip(bins); spec=standards_zip()
    # public docs
    for name in [f'saga-REVIEW_REPORT-{VERSION}.md',f'saga-VALIDATION-{VERSION}.md',f'SAGA_REVIEW_HANDOFF_{VERSION}.md',f'SAGA_PLATFORM_QUALIFICATION_{VERSION}.md','SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md',f'release/source-manifest-{VERSION}.json',f'validation/production-ga-{VERSION}.json']:
        src=ROOT/name; dst=OUT/Path(name).name; shutil.copy2(src,dst)
    public=[src,iz,sdk,spec,*bins,OUT/f'saga-REVIEW_REPORT-{VERSION}.md',OUT/f'saga-VALIDATION-{VERSION}.md',OUT/f'SAGA_REVIEW_HANDOFF_{VERSION}.md',OUT/f'SAGA_PLATFORM_QUALIFICATION_{VERSION}.md',OUT/'SAGA_LANGUAGE_SPECIFICATION_1.0_FINAL_CANDIDATE.md',OUT/f'source-manifest-{VERSION}.json',OUT/f'production-ga-{VERSION}.json']
    checks=OUT/f'saga-{VERSION}-checksums.txt';checks.write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in public))
    print('\n'.join(map(str,[*public,checks])))
if __name__=='__main__': main()
