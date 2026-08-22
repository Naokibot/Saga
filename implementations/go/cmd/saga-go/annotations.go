package main

func annotationHasStringArg(items []Annotation, name, arg string) bool {
	for _, a := range items {
		if a.Name != name {
			continue
		}
		for _, raw := range a.Args {
			if lit, ok := raw.(*Literal); ok {
				if s, ok := lit.Value.(string); ok && s == arg {
					return true
				}
			}
		}
	}
	return false
}

func classDerives(ci *ClassInfo, capability string) bool {
	return ci != nil && ci.Decl != nil && annotationHasStringArg(ci.Decl.Annotations, "derive", capability)
}
