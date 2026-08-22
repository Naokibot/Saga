package main

import "testing"

func TestUnicode151IdentifierProfile(t *testing.T) {
	if !isStart('日') || !isContinue('本') || !isContinue('1') {
		t.Fatal("expected Japanese letters and decimal digit to be valid identifier characters")
	}
	if isStart('1') || isStart('😀') || isContinue('😀') {
		t.Fatal("invalid identifier character accepted")
	}
	if normalizeNFC("cafe\u0301") != "café" {
		t.Fatal("NFC normalization mismatch")
	}
}
