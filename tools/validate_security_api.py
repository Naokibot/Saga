#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.38.0'
m=json.loads((ROOT/f'compatibility/security-api-{REL}.json').read_text())
checker=(ROOT/'implementations/go/cmd/saga-go/checker.go').read_text()
runtime=(ROOT/'implementations/go/cmd/saga-go/security_native.go').read_text()
python=(ROOT/'saga/stdlib/modules.py').read_text()
tests=(ROOT/'implementations/go/cmd/saga-go/security_native_test.go').read_text()
sec=m['native_security_functions']; crypto=m['crypto_extensions']
checks={
    'native_security_checker': all(f'"{x}"' in checker[checker.index('if t.Name == "module:security"'):checker.index('if t.Name == "module:net"')] for x in sec),
    'native_security_runtime': all(f'"{x}"' in runtime for x in sec),
    'native_crypto_checker': all(f'"{x}"' in checker[checker.index('if t.Name == "module:crypto"'):checker.index('if t.Name == "module:security"')] for x in crypto),
    'native_crypto_runtime': all(f'"{x}"' in runtime for x in crypto),
    'python_security_surface': all(f'@native("security", "{x}"' in python for x in sec),
    'known_hmac_vector_test': 'f7bc83f430538424b13298e6aa6fb143' in tests,
    'pbkdf2_known_vector_test': '120fb6cffcf8b32c43e7225256c4f837' in tests,
    'aes_tamper_test': 'tampered' in tests,
    'real_tls_chain_test': 'tls.Listen' in tests and 'tls_probe' in tests,
    'cross_process_db_test': 'TestKVDBMultiProcessNoLostUpdateAndConflict' in tests,
}
report={'schema':1,'release':REL,'profile':m['profile'],'native_security_count':len(sec),'crypto_extension_count':len(crypto),'checks':checks,'pass':all(checks.values())}
out=ROOT/f'validation/security-api-{REL}.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['pass'] else 1)
