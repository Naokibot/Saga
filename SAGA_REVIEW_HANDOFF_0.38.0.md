# Saga 0.38.0 reviewer handoff

Review focus:
1. incremental minor/nursery collector state machine, allocation barrier, write barrier, remembered old->young edges and promotion;
2. preservation of Native Runtime ABI 0.35 compatibility while adding feature-level 0.38 APIs;
3. Windows/macOS evidence labeling (cross-built/static, never physical PASS);
4. OS-level HIL simulation using PTY UART and virtual CAN, plus deterministic 168-hour twin;
5. real registry HTTP paths under virtual-user load, with public Internet/adoption explicitly unavailable;
6. functional-safety pre-certification evidence and the explicit `NOT_CERTIFIED` boundary.
