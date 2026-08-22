package main

import "testing"

func TestObjectGraphPreservesNamespacedModuleSemantics(t *testing.T) {
	sources := map[string]string{
		"project/models.saga": "module models\npublic fn twice(value: int) -> int = value * 2\ninternal fn hidden() -> int = 99\n",
		"project/main.saga":   "use \"models.saga\" as m\nprint(m.twice(21))\n",
	}
	edges := map[string]string{"project/main.saga\x00models.saga": "project/models.saga"}
	stmts, err := loadObjectGraphProgram("project/main.saga", sources, edges)
	if err != nil {
		t.Fatal(err)
	}
	checker := NewChecker()
	if err = checker.Check(stmts); err != nil {
		t.Fatal(err)
	}
}

func TestObjectGraphRejectsMissingResolvedEdge(t *testing.T) {
	sources := map[string]string{"project/main.saga": "use \"models.saga\" as m\nprint(1)\n"}
	if _, err := loadObjectGraphProgram("project/main.saga", sources, map[string]string{}); err == nil {
		t.Fatal("expected missing object graph edge to fail")
	}
}
