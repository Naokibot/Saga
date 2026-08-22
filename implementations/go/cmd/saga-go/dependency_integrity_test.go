package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func makeLockedDependencyFixture(t *testing.T) (string, string, string) {
	t.Helper()
	root := t.TempDir()
	pkg := filepath.Join(root, "vendor", "math-tools", "1.0.0")
	if err := os.MkdirAll(pkg, 0755); err != nil {
		t.Fatal(err)
	}
	manifest := "[project]\nname=\"math-tools\"\nversion=\"1.0.0\"\nlanguage=\"1.0\"\nentry=\"lib.saga\"\ntest_dir=\"tests\"\n"
	if err := os.WriteFile(filepath.Join(pkg, "saga.toml"), []byte(manifest), 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(pkg, "lib.saga"), []byte("fn twice(x:int)->int=x*2\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := writeLock(pkg); err != nil {
		t.Fatal(err)
	}
	artifact := filepath.Join(root, "math-tools.sagapkg")
	if _, err := packProject(pkg, artifact); err != nil {
		t.Fatal(err)
	}
	digest, _, err := fileDigest(artifact)
	if err != nil {
		t.Fatal(err)
	}
	dep := dependencyLock{Packages: map[string]dependencyRecord{
		"math-tools": {Version: "1.0.0", SHA256: digest, Path: "vendor/math-tools/1.0.0"},
	}}
	raw, _ := json.MarshalIndent(dep, "", "  ")
	if err := os.WriteFile(filepath.Join(root, "saga.dependencies.json"), append(raw, '\n'), 0644); err != nil {
		t.Fatal(err)
	}
	entry := filepath.Join(root, "main.saga")
	if err := os.WriteFile(entry, []byte("use \"pkg:math-tools/lib.saga\"\nprint(twice(21))\n"), 0644); err != nil {
		t.Fatal(err)
	}
	return root, pkg, entry
}

func TestPackageImportRejectsPostInstallTampering(t *testing.T) {
	_, pkg, entry := makeLockedDependencyFixture(t)
	if _, err := loadProgram(entry); err != nil {
		t.Fatalf("clean dependency rejected: %v", err)
	}
	if err := os.WriteFile(filepath.Join(pkg, "lib.saga"), []byte("fn twice(x:int)->int=x*99\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := loadProgram(entry); err == nil || !strings.Contains(err.Error(), "integrity verification failed") {
		t.Fatalf("tampered dependency was not rejected: %v", err)
	}
}

func TestPackageImportRejectsUntrackedAddedSource(t *testing.T) {
	root, pkg, _ := makeLockedDependencyFixture(t)
	if err := os.WriteFile(filepath.Join(pkg, "evil.saga"), []byte("fn injected()->int=99\n"), 0644); err != nil {
		t.Fatal(err)
	}
	entry := filepath.Join(root, "untracked.saga")
	if err := os.WriteFile(entry, []byte("use \"pkg:math-tools/evil.saga\"\nprint(injected())\n"), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := loadProgram(entry); err == nil || !strings.Contains(err.Error(), "not tracked by saga.lock") {
		t.Fatalf("untracked dependency source was not rejected: %v", err)
	}
}

func TestPackageImportRejectsDuplicateDependencyLockKeys(t *testing.T) {
	root, _, entry := makeLockedDependencyFixture(t)
	bad := `{"packages":{"math-tools":{"version":"1.0.0","sha256":"` + strings.Repeat("0", 64) + `","path":"vendor/math-tools/1.0.0"},"math-tools":{"version":"1.0.0","sha256":"` + strings.Repeat("0", 64) + `","path":"vendor/math-tools/1.0.0"}}}`
	if err := os.WriteFile(filepath.Join(root, "saga.dependencies.json"), []byte(bad), 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := loadProgram(entry); err == nil || !strings.Contains(err.Error(), "strict JSON") {
		t.Fatalf("duplicate dependency key was not rejected: %v", err)
	}
}

func TestConcurrentRegistryAddsPreserveDependencyRecords(t *testing.T) {
	project := t.TempDir()
	type fixture struct {
		name string
		data []byte
		sig  packageSignature
	}
	fixtures := make([]fixture, 0, 2)
	for _, name := range []string{"alpha-pkg", "beta-pkg"} {
		data := makeRegistryTestPackage(t, name, "1.0.0")
		_, priv, err := ed25519.GenerateKey(rand.Reader)
		if err != nil {
			t.Fatal(err)
		}
		fixtures = append(fixtures, fixture{name: name, data: data, sig: signBytes(data, priv)})
	}
	arrived := make(chan struct{}, 2)
	release := make(chan struct{})
	servers := make([]*httptest.Server, 0, 2)
	for i := range fixtures {
		fx := fixtures[i]
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			arrived <- struct{}{}
			<-release
			writeRegistryRawResponse(w, fx.data, fx.sig)
		}))
		servers = append(servers, srv)
		defer srv.Close()
	}
	var wg sync.WaitGroup
	errs := make(chan error, 2)
	for i := range fixtures {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			errs <- registryAdd(project, fixtures[i].name+"@1.0.0", servers[i].URL, fixtures[i].sig.Fingerprint)
		}(i)
	}
	<-arrived
	<-arrived
	close(release)
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Fatalf("concurrent registry add failed: %v", err)
		}
	}
	raw, err := os.ReadFile(filepath.Join(project, "saga.dependencies.json"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err = decodeJSONSaga(string(raw)); err != nil {
		t.Fatal(err)
	}
	var dep dependencyLock
	if err = json.Unmarshal(raw, &dep); err != nil {
		t.Fatal(err)
	}
	if len(dep.Packages) != 2 {
		t.Fatalf("lost dependency record after concurrent add: %#v", dep.Packages)
	}
	if _, ok := dep.Packages["alpha-pkg"]; !ok {
		t.Fatal("alpha-pkg dependency record missing")
	}
	if _, ok := dep.Packages["beta-pkg"]; !ok {
		t.Fatal("beta-pkg dependency record missing")
	}
}

func TestPackProjectRefusesToOverwriteInputs(t *testing.T) {
	root := t.TempDir()
	manifest := "[project]\nname=\"protect-input\"\nversion=\"1.0.0\"\nlanguage=\"1.0\"\nentry=\"main.saga\"\ntest_dir=\"tests\"\n"
	if err := os.WriteFile(filepath.Join(root, "saga.toml"), []byte(manifest), 0644); err != nil {
		t.Fatal(err)
	}
	source := filepath.Join(root, "main.saga")
	original := []byte("print(1)\n")
	if err := os.WriteFile(source, original, 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := writeLock(root); err != nil {
		t.Fatal(err)
	}
	if _, err := packProject(root, source); err == nil || !strings.Contains(err.Error(), "may not overwrite") {
		t.Fatalf("pack did not reject source overwrite: %v", err)
	}
	got, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(original) {
		t.Fatalf("source changed after rejected pack: %q", got)
	}
}

func TestPackProjectRefusesSymlinkAliasOverwrite(t *testing.T) {
	root := t.TempDir()
	manifest := "[project]\nname=\"protect-alias\"\nversion=\"1.0.0\"\nlanguage=\"1.0\"\nentry=\"main.saga\"\ntest_dir=\"tests\"\n"
	if err := os.WriteFile(filepath.Join(root, "saga.toml"), []byte(manifest), 0644); err != nil {
		t.Fatal(err)
	}
	source := filepath.Join(root, "main.saga")
	original := []byte("print(1)\n")
	if err := os.WriteFile(source, original, 0644); err != nil {
		t.Fatal(err)
	}
	if _, err := writeLock(root); err != nil {
		t.Fatal(err)
	}
	aliasParent := filepath.Join(t.TempDir(), "project-link")
	if err := os.Symlink(root, aliasParent); err != nil {
		t.Skipf("symlink unavailable: %v", err)
	}
	aliasOut := filepath.Join(aliasParent, "main.saga")
	if _, err := packProject(root, aliasOut); err == nil || !strings.Contains(err.Error(), "may not overwrite") {
		t.Fatalf("pack did not reject symlink-alias source overwrite: %v", err)
	}
	got, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(original) {
		t.Fatalf("source changed after rejected alias pack: %q", got)
	}
}

func TestPackageMemberSnapshotRejectsContentChangedAfterLock(t *testing.T) {
	good := []byte("print(1)\n")
	h := sha256.Sum256(good)
	records := map[string]LockFileRecord{
		"main.saga": {Path: "main.saga", SHA256: hex.EncodeToString(h[:]), Size: int64(len(good))},
	}
	if err := validatePackageMemberSnapshot("main.saga", good, records); err != nil {
		t.Fatal(err)
	}
	if err := validatePackageMemberSnapshot("main.saga", []byte("print(2)\n"), records); err == nil || !strings.Contains(err.Error(), "changed while packing") {
		t.Fatalf("stale lock did not reject changed pack member: %v", err)
	}
}
