#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "implementations/go/cmd/saga-go/generic_adts_051_test.go"
text = path.read_text(encoding="utf-8")

old_import = '''import (\n    "strings"\n    "testing"\n)\n'''
new_import = '''import (\n    "testing"\n)\n'''
if old_import not in text:
    raise RuntimeError("generic ADT test import block changed unexpectedly")
text = text.replace(old_import, new_import, 1)

old_test = '''func TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {\n    _, err := runSagaForTest(t, `enum Maybe[T] { None, Some(T) }\nlet value = Maybe.None`)\n    if err == nil || !strings.Contains(err.Error(), "SAGA-T113") {\n        t.Fatalf("expected SAGA-T113, got %v", err)\n    }\n}\n'''
new_test = '''func TestGenericADT051NullaryVariantNeedsContext(t *testing.T) {\n    _, err := runSagaForTest(t, `enum Maybe[T] { None, Some(T) }\nlet value = Maybe.None`)\n    sagaErr, ok := err.(*SagaError)\n    if !ok || sagaErr.ID != "SAGA-T113" {\n        t.Fatalf("expected SagaError ID SAGA-T113, got %#v", err)\n    }\n}\n'''
if old_test not in text:
    raise RuntimeError("generic ADT diagnostic test changed unexpectedly")
text = text.replace(old_test, new_test, 1)
path.write_text(text, encoding="utf-8")
print("Saga 0.51 Go diagnostic assertion fix staged successfully")
