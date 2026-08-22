package main

import (
	"crypto/sha256"
	"encoding/binary"
	"os"
)

func writeSyntheticBundle(path string, runtimeBytes, payload, footer []byte) error {
	binary.LittleEndian.PutUint64(footer[8:16], uint64(len(payload)))
	h := sha256.Sum256(payload)
	copy(footer[16:48], h[:])
	data := append(append(append([]byte{}, runtimeBytes...), payload...), footer...)
	return os.WriteFile(path, data, 0755)
}
